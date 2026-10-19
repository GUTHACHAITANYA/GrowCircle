"""
Photo Fraud Detection Engine for Agricultural Produce Listings (Phase ML-4).
Detects:
1. Timestamp inconsistencies (EXIF DateTimeOriginal vs server upload time > 24h).
2. Geolocation inconsistencies (EXIF GPS vs farm coordinates > 25 km).
3. Near-duplicate images across listings (dHash, aHash, and DCT-based pHash).
4. Screenshot-of-a-screen detection (Moire FFT grid artifacts, display aspect ratios, EXIF absence).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np
from PIL import ExifTags, Image
from scipy import fftpack


def compute_ahash(image: Image.Image, hash_size: int = 8) -> str:
    """Average Hash: Compares pixel intensity to overall image mean."""
    gray = image.convert("L").resize((hash_size, hash_size), Image.Resampling.LANCZOS)
    pixels = np.array(gray, dtype=float)
    avg = pixels.mean()
    bits = (pixels > avg).flatten()
    return f"{int(''.join(['1' if b else '0' for b in bits]), 2):016x}"


def compute_dhash(image: Image.Image, hash_size: int = 8) -> str:
    """Difference Hash: Compares adjacent horizontal pixel gradients. Highly robust to lighting."""
    gray = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = np.array(gray, dtype=float)
    diff = pixels[:, 1:] > pixels[:, :-1]
    bits = diff.flatten()
    return f"{int(''.join(['1' if b else '0' for b in bits]), 2):016x}"


def compute_phash(image: Image.Image, hash_size: int = 8, highfreq_factor: int = 4) -> str:
    """
    Perceptual Hash via 2D Discrete Cosine Transform (DCT).
    Extracts robust low-frequency spectral coefficients, ignoring high-frequency noise and compression.
    """
    img_size = hash_size * highfreq_factor
    gray = image.convert("L").resize((img_size, img_size), Image.Resampling.LANCZOS)
    pixels = np.array(gray, dtype=float)
    dct = fftpack.dct(fftpack.dct(pixels, axis=0, norm="ortho"), axis=1, norm="ortho")
    # Low frequency top-left 8x8 block (excluding DC component [0,0])
    dct_low = dct[:hash_size, :hash_size]
    med = np.median(dct_low.flatten()[1:])
    bits = (dct_low > med).flatten()
    return f"{int(''.join(['1' if b else '0' for b in bits]), 2):016x}"


def compute_perceptual_hashes(image: Image.Image) -> dict[str, str]:
    """Computes aHash, dHash, and pHash for an image."""
    return {
        "ahash": compute_ahash(image),
        "dhash": compute_dhash(image),
        "phash": compute_phash(image),
    }


def hamming_distance(hash1: str, hash2: str) -> int:
    """Calculates bit-level Hamming distance between two hex hashes."""
    try:
        val1 = int(hash1, 16)
        val2 = int(hash2, 16)
        return bin(val1 ^ val2).count("1")
    except ValueError:
        return 64


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two GPS coordinates in kilometers."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    return round(2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a)), 2)


def convert_gps_to_decimal(coords: tuple[Any, Any, Any], ref: str) -> float | None:
    """Converts EXIF GPS degrees, minutes, seconds rational tuples to decimal degrees."""
    try:
        def to_float(val: Any) -> float:
            if hasattr(val, "numerator") and hasattr(val, "denominator"):
                return float(val.numerator) / float(val.denominator) if val.denominator != 0 else 0.0
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, tuple) and len(val) == 2:
                return float(val[0]) / float(val[1]) if val[1] != 0 else 0.0
            return float(val)

        deg = to_float(coords[0])
        minutes = to_float(coords[1])
        seconds = to_float(coords[2])
        decimal = deg + (minutes / 60.0) + (seconds / 3600.0)
        if ref in ["S", "W"]:
            decimal = -decimal
        return round(decimal, 6)
    except Exception:
        return None


def extract_exif(image: Image.Image) -> dict[str, Any]:
    """Extracts parsed EXIF tags including camera details, timestamp, and GPS."""
    exif_data: dict[str, Any] = {
        "has_exif": False,
        "make": None,
        "model": None,
        "datetime_original": None,
        "software": None,
        "latitude": None,
        "longitude": None,
        "is_camera_raw": False,
    }

    raw_exif = image.getexif()
    if not raw_exif:
        return exif_data

    exif_data["has_exif"] = True
    tags = {ExifTags.TAGS.get(k, k): v for k, v in raw_exif.items()}

    exif_data["make"] = tags.get("Make")
    exif_data["model"] = tags.get("Model")
    exif_data["datetime_original"] = tags.get("DateTimeOriginal") or tags.get("DateTime")
    exif_data["software"] = tags.get("Software")

    # Check GPS info if available
    gps_info_raw = None
    for tag, value in raw_exif.items():
        if ExifTags.TAGS.get(tag) == "GPSInfo":
            gps_info_raw = value
            break

    if gps_info_raw and isinstance(gps_info_raw, dict):
        lat_coords = gps_info_raw.get(2)
        lat_ref = gps_info_raw.get(1, "N")
        lon_coords = gps_info_raw.get(4)
        lon_ref = gps_info_raw.get(3, "E")

        if lat_coords and lon_coords:
            exif_data["latitude"] = convert_gps_to_decimal(lat_coords, str(lat_ref))
            exif_data["longitude"] = convert_gps_to_decimal(lon_coords, str(lon_ref))

    if exif_data["make"] and exif_data["model"]:
        exif_data["is_camera_raw"] = True

    return exif_data


def detect_screenshot_of_screen(image: Image.Image, exif_data: dict[str, Any]) -> tuple[bool, float, list[str]]:
    """
    Detects if the photo is a screenshot or a photo taken of another computer/phone screen.
    Signals:
    1. EXIF lack of sensor metadata or Software tag mentioning screenshot.
    2. Phone screen aspect ratios (16:9, 19.5:9, 20:9, 21:9).
    3. 2D FFT Moire high-frequency harmonic energy peak from LCD/OLED pixel grids.
    """
    reasons: list[str] = []
    score = 0.0
    w, h = image.size

    # 1. EXIF Software & Camera tags
    software = str(exif_data.get("software") or "").lower()
    if any(k in software for k in ["screenshot", "screen capture", "screencap", "android", "snipping"]):
        score += 0.60
        reasons.append(f"EXIF software tag indicates screenshot utility: '{software}'")

    if not exif_data.get("has_exif") or not exif_data.get("is_camera_raw"):
        score += 0.15
        reasons.append("Missing standard optical camera sensor EXIF tags (Make, Model, Shutter, ISO)")

    # 2. Aspect Ratio Heuristics
    ratio = max(w, h) / max(min(w, h), 1)
    screen_ratios = [
        (16.0 / 9.0, "16:9 standard display"),
        (19.5 / 9.0, "19.5:9 modern smartphone"),
        (20.0 / 9.0, "20:9 smartphone display"),
        (20.5 / 9.0, "20.5:9 tall phone screen"),
    ]
    for target_ratio, label in screen_ratios:
        if abs(ratio - target_ratio) <= 0.025:
            score += 0.20
            reasons.append(f"Dimensions ({w}x{h}, aspect {ratio:.3f}) match exact {label}")
            break

    # 3. Frequency Domain Moire Grid Pattern Analysis
    try:
        small_gray = image.convert("L").resize((128, 128), Image.Resampling.LANCZOS)
        arr = np.array(small_gray, dtype=float)
        # 2D FFT and magnitude spectrum
        f2 = np.fft.fft2(arr - arr.mean())
        fshift = np.fft.fftshift(f2)
        magnitude = np.abs(fshift)

        # Check high-frequency corner spikes indicative of periodic raster screen lines
        center = 64
        high_freq_mask = np.ones((128, 128), dtype=bool)
        high_freq_mask[center - 24 : center + 24, center - 24 : center + 24] = False

        high_freq_energy = magnitude[high_freq_mask]
        peak_to_mean = float(np.max(high_freq_energy) / (np.mean(high_freq_energy) + 1e-6))

        if peak_to_mean > 12.0:
            score += 0.35
            reasons.append(f"2D FFT frequency spectrum reveals prominent Moire LCD subpixel peak (ratio {peak_to_mean:.1f})")
    except Exception:
        pass

    is_screenshot = score >= 0.45
    return is_screenshot, round(min(score, 1.0), 3), reasons


@dataclass
class PhotoFraudReport:
    is_suspicious: bool
    fraud_risk_score: float  # 0.0 to 1.0
    recommendation: str  # 'PASS', 'BUYER_VERIFY', 'FLAGGED_SUSPICIOUS'
    timestamp_check: dict[str, Any]
    location_check: dict[str, Any]
    duplicate_check: dict[str, Any]
    screenshot_check: dict[str, Any]
    perceptual_hashes: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_suspicious": self.is_suspicious,
            "fraud_risk_score": self.fraud_risk_score,
            "recommendation": self.recommendation,
            "timestamp_check": self.timestamp_check,
            "location_check": self.location_check,
            "duplicate_check": self.duplicate_check,
            "screenshot_check": self.screenshot_check,
            "perceptual_hashes": self.perceptual_hashes,
        }


class PhotoFraudChecker:
    """
    Evaluates produce listing photos against physical reality and database inventory.
    """

    def __init__(self, max_allowed_age_hours: float = 24.0, max_gps_distance_km: float = 25.0) -> None:
        self.max_age_hours = max_allowed_age_hours
        self.max_gps_km = max_gps_distance_km

    def check_photo(
        self,
        image: Image.Image,
        listing_farm_coords: tuple[float, float] | None = None,
        existing_listing_hashes: list[dict[str, Any]] | None = None,
        server_timestamp: datetime | None = None,
    ) -> PhotoFraudReport:
        """
        Executes complete fraud verification checklist on a candidate lot photograph.
        """
        now = server_timestamp or datetime.now(UTC)
        exif = extract_exif(image)
        hashes = compute_perceptual_hashes(image)

        fraud_score = 0.0

        # 1. Timestamp Consistency Check
        ts_check: dict[str, Any] = {
            "passed": True,
            "exif_timestamp": exif.get("datetime_original"),
            "server_timestamp": now.isoformat(),
            "age_hours": None,
            "flag": None,
        }
        if exif.get("datetime_original"):
            try:
                # Standard EXIF format: 'YYYY:MM:DD HH:MM:SS'
                clean_ts = exif["datetime_original"].strip().replace("-", ":")
                dt_obj = datetime.strptime(clean_ts[:19], "%Y:%m:%d %H:%M:%S").replace(tzinfo=UTC)
                diff_sec = (now - dt_obj).total_seconds()
                diff_hours = diff_sec / 3600.0
                ts_check["age_hours"] = round(diff_hours, 2)

                if diff_hours > self.max_age_hours:
                    ts_check["passed"] = False
                    ts_check["flag"] = f"Photo is {diff_hours:.1f} hours old (> 24h limit for fresh lots)"
                    fraud_score += 0.35
                elif diff_hours < -0.1:  # Future timestamped
                    ts_check["passed"] = False
                    ts_check["flag"] = "Photo timestamp is in the future relative to server time"
                    fraud_score += 0.40
            except Exception as e:
                ts_check["flag"] = f"Unparseable EXIF datetime format: {e}"

        # 2. Location Consistency Check
        loc_check: dict[str, Any] = {
            "passed": True,
            "exif_lat": exif.get("latitude"),
            "exif_lon": exif.get("longitude"),
            "distance_km": None,
            "status": "unverified",
        }
        if exif.get("latitude") is not None and exif.get("longitude") is not None:
            if listing_farm_coords is not None:
                farm_lat, farm_lon = listing_farm_coords
                dist_km = haversine_distance_km(exif["latitude"], exif["longitude"], farm_lat, farm_lon)
                loc_check["distance_km"] = dist_km
                if dist_km > self.max_gps_km:
                    loc_check["passed"] = False
                    loc_check["status"] = f"GPS mismatch: Photo taken {dist_km} km away from registered farm (> {self.max_gps_km} km limit)"
                    fraud_score += 0.45
                else:
                    loc_check["status"] = f"Verified: Photo taken {dist_km} km from farm (within limit)"
            else:
                loc_check["status"] = "GPS present in photo but listing coordinates not provided"
        else:
            loc_check["status"] = "No GPS tags in photo; marked location-unverified"

        # 3. Near-Duplicate Detection across existing listings
        dup_check: dict[str, Any] = {
            "is_duplicate": False,
            "min_hamming_distance": 64,
            "matched_listing_id": None,
            "details": "No duplicates detected",
        }
        cand_phash = hashes["phash"]
        cand_dhash = hashes["dhash"]

        if existing_listing_hashes:
            for item in existing_listing_hashes:
                ref_phash = item.get("phash") or item.get("hash")
                ref_dhash = item.get("dhash")
                if ref_phash:
                    p_dist = hamming_distance(cand_phash, ref_phash)
                    d_dist = hamming_distance(cand_dhash, ref_dhash) if ref_dhash else p_dist
                    effective_dist = min(p_dist, d_dist)

                    if effective_dist < dup_check["min_hamming_distance"]:
                        dup_check["min_hamming_distance"] = effective_dist
                        dup_check["matched_listing_id"] = item.get("listing_id")

                    # Near-duplicate threshold: distance <= 6 bits out of 64
                    if effective_dist <= 6:
                        dup_check["is_duplicate"] = True
                        dup_check["details"] = f"Near-duplicate match found with Listing #{item.get('listing_id')} (Hamming distance {effective_dist}/64)"
                        fraud_score += 0.55
                        break

        # 4. Screenshot of a screen detection
        is_screen, screen_score, screen_reasons = detect_screenshot_of_screen(image, exif)
        screen_check: dict[str, Any] = {
            "is_screenshot": is_screen,
            "confidence": screen_score,
            "reasons": screen_reasons,
        }
        if is_screen:
            fraud_score += 0.35

        final_score = round(min(fraud_score, 1.0), 3)
        is_suspicious = final_score >= 0.40

        if final_score < 0.25:
            recommendation = "PASS"
        elif final_score < 0.55:
            recommendation = "BUYER_VERIFY"
        else:
            recommendation = "FLAGGED_SUSPICIOUS"

        return PhotoFraudReport(
            is_suspicious=is_suspicious,
            fraud_risk_score=final_score,
            recommendation=recommendation,
            timestamp_check=ts_check,
            location_check=loc_check,
            duplicate_check=dup_check,
            screenshot_check=screen_check,
            perceptual_hashes=hashes,
        )
