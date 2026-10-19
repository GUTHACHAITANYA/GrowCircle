"""
Pincode lookup service for India / Andhra Pradesh.
Maps 6-digit postal index codes to latitude, longitude, mandal, district, and state.
Used as non-blocking fallback when GPS permission is denied or unavailable.
"""

from typing import Any

# Curated reference mapping for Andhra Pradesh and surrounding major agricultural hubs
EXPLICIT_PINCODE_MAP: dict[str, dict[str, Any]] = {
    # Guntur District
    "522001": {"district": "Guntur", "state": "Andhra Pradesh", "mandal": "Guntur", "latitude": 16.3067, "longitude": 80.4365},
    "522002": {"district": "Guntur", "state": "Andhra Pradesh", "mandal": "Guntur", "latitude": 16.3100, "longitude": 80.4400},
    "522003": {"district": "Guntur", "state": "Andhra Pradesh", "mandal": "Guntur", "latitude": 16.2950, "longitude": 80.4200},
    "522004": {"district": "Guntur", "state": "Andhra Pradesh", "mandal": "Guntur", "latitude": 16.3200, "longitude": 80.4500},
    "522006": {"district": "Guntur", "state": "Andhra Pradesh", "mandal": "Guntur", "latitude": 16.3150, "longitude": 80.4300},
    "522007": {"district": "Guntur", "state": "Andhra Pradesh", "mandal": "Guntur", "latitude": 16.2800, "longitude": 80.4100},
    "522201": {"district": "Guntur", "state": "Andhra Pradesh", "mandal": "Tenali", "latitude": 16.2430, "longitude": 80.6400},
    "522202": {"district": "Guntur", "state": "Andhra Pradesh", "mandal": "Tenali", "latitude": 16.2350, "longitude": 80.6450},
    "522503": {"district": "Guntur", "state": "Andhra Pradesh", "mandal": "Mangalagiri", "latitude": 16.4300, "longitude": 80.5700},
    "522124": {"district": "Guntur", "state": "Andhra Pradesh", "mandal": "Ponnur", "latitude": 16.0667, "longitude": 80.5500},
    "522212": {"district": "Guntur", "state": "Andhra Pradesh", "mandal": "Chebrolu", "latitude": 16.1989, "longitude": 80.5303},
    "522019": {"district": "Guntur", "state": "Andhra Pradesh", "mandal": "Prathipadu", "latitude": 16.1833, "longitude": 80.3333},
    # NTR / Krishna District
    "520001": {"district": "NTR", "state": "Andhra Pradesh", "mandal": "Vijayawada Urban", "latitude": 16.5062, "longitude": 80.6480},
    "520002": {"district": "NTR", "state": "Andhra Pradesh", "mandal": "Vijayawada Urban", "latitude": 16.5150, "longitude": 80.6350},
    "520003": {"district": "NTR", "state": "Andhra Pradesh", "mandal": "Vijayawada Urban", "latitude": 16.5200, "longitude": 80.6200},
    "520010": {"district": "NTR", "state": "Andhra Pradesh", "mandal": "Vijayawada Urban", "latitude": 16.4950, "longitude": 80.6550},
    "521456": {"district": "NTR", "state": "Andhra Pradesh", "mandal": "Ibrahimpatnam", "latitude": 16.5833, "longitude": 80.5167},
    "521185": {"district": "NTR", "state": "Andhra Pradesh", "mandal": "Nandigama", "latitude": 16.7833, "longitude": 80.3000},
    # Annamayya / Chittoor
    "517325": {"district": "Annamayya", "state": "Andhra Pradesh", "mandal": "Madanapalle", "latitude": 13.5500, "longitude": 78.5000},
    "517326": {"district": "Annamayya", "state": "Andhra Pradesh", "mandal": "Madanapalle", "latitude": 13.5600, "longitude": 78.5100},
    "517257": {"district": "Annamayya", "state": "Andhra Pradesh", "mandal": "Somala", "latitude": 13.4475, "longitude": 78.8686},
    "516269": {"district": "Annamayya", "state": "Andhra Pradesh", "mandal": "Rayachoti", "latitude": 14.0500, "longitude": 78.7500},
    # Tirupati District
    "517501": {"district": "Tirupati", "state": "Andhra Pradesh", "mandal": "Tirupati Urban", "latitude": 13.6288, "longitude": 79.4192},
    "517502": {"district": "Tirupati", "state": "Andhra Pradesh", "mandal": "Tirupati Rural", "latitude": 13.6000, "longitude": 79.4000},
    "517644": {"district": "Tirupati", "state": "Andhra Pradesh", "mandal": "Srikalahasti", "latitude": 13.7500, "longitude": 79.7000},
    # Kurnool District
    "518001": {"district": "Kurnool", "state": "Andhra Pradesh", "mandal": "Kurnool", "latitude": 15.8281, "longitude": 78.0373},
    "518002": {"district": "Kurnool", "state": "Andhra Pradesh", "mandal": "Kurnool", "latitude": 15.8200, "longitude": 78.0400},
    "518301": {"district": "Kurnool", "state": "Andhra Pradesh", "mandal": "Adoni", "latitude": 15.6300, "longitude": 77.2700},
    # Anantapur District
    "515001": {"district": "Anantapur", "state": "Andhra Pradesh", "mandal": "Anantapur", "latitude": 14.6819, "longitude": 77.6006},
    "515401": {"district": "Anantapur", "state": "Andhra Pradesh", "mandal": "Tadipatri", "latitude": 14.9100, "longitude": 78.0100},
    # East Godavari District
    "533101": {"district": "East Godavari", "state": "Andhra Pradesh", "mandal": "Rajahmundry Urban", "latitude": 17.0005, "longitude": 81.8040},
    "533102": {"district": "East Godavari", "state": "Andhra Pradesh", "mandal": "Rajahmundry Rural", "latitude": 17.0200, "longitude": 81.7800},
    # Prakasam District
    "523001": {"district": "Prakasam", "state": "Andhra Pradesh", "mandal": "Ongole", "latitude": 15.5057, "longitude": 80.0499},
    "523303": {"district": "Prakasam", "state": "Andhra Pradesh", "mandal": "Santhamaguluru", "latitude": 16.0333, "longitude": 80.0333},
}

# 3-digit prefix regional defaults for graceful fallback across South India
PREFIX_REGION_DEFAULTS: dict[str, dict[str, Any]] = {
    "522": {"district": "Guntur", "state": "Andhra Pradesh", "mandal": "Guntur", "latitude": 16.3067, "longitude": 80.4365},
    "520": {"district": "NTR", "state": "Andhra Pradesh", "mandal": "Vijayawada Urban", "latitude": 16.5062, "longitude": 80.6480},
    "521": {"district": "Krishna", "state": "Andhra Pradesh", "mandal": "Machilipatnam", "latitude": 16.1875, "longitude": 81.1389},
    "517": {"district": "Tirupati", "state": "Andhra Pradesh", "mandal": "Tirupati Urban", "latitude": 13.6288, "longitude": 79.4192},
    "518": {"district": "Kurnool", "state": "Andhra Pradesh", "mandal": "Kurnool", "latitude": 15.8281, "longitude": 78.0373},
    "515": {"district": "Anantapur", "state": "Andhra Pradesh", "mandal": "Anantapur", "latitude": 14.6819, "longitude": 77.6006},
    "533": {"district": "East Godavari", "state": "Andhra Pradesh", "mandal": "Rajahmundry Urban", "latitude": 17.0005, "longitude": 81.8040},
    "523": {"district": "Prakasam", "state": "Andhra Pradesh", "mandal": "Ongole", "latitude": 15.5057, "longitude": 80.0499},
    "530": {"district": "Visakhapatnam", "state": "Andhra Pradesh", "mandal": "Visakhapatnam Urban", "latitude": 17.6868, "longitude": 83.2185},
    "500": {"district": "Hyderabad", "state": "Telangana", "mandal": "Hyderabad", "latitude": 17.3850, "longitude": 78.4867},
    "560": {"district": "Bengaluru Urban", "state": "Karnataka", "mandal": "Bengaluru", "latitude": 12.9716, "longitude": 77.5946},
    "600": {"district": "Chennai", "state": "Tamil Nadu", "mandal": "Chennai", "latitude": 13.0827, "longitude": 80.2707},
}


class PincodeService:
    """Resolves Indian 6-digit pincodes to geographic coordinates and administrative units."""

    @classmethod
    def lookup(cls, pincode: str) -> dict[str, Any] | None:
        clean = pincode.strip().replace(" ", "")
        if not clean.isdigit() or len(clean) != 6:
            return None

        # 1. Exact match
        if clean in EXPLICIT_PINCODE_MAP:
            entry = EXPLICIT_PINCODE_MAP[clean]
            return {
                "pincode": clean,
                "district": entry["district"],
                "state": entry["state"],
                "mandal": entry["mandal"],
                "latitude": entry["latitude"],
                "longitude": entry["longitude"],
                "lat": entry["latitude"],
                "lng": entry["longitude"],
                "is_exact": True,
            }

        # 2. 3-digit prefix regional match
        prefix = clean[:3]
        if prefix in PREFIX_REGION_DEFAULTS:
            entry = PREFIX_REGION_DEFAULTS[prefix]
            return {
                "pincode": clean,
                "district": entry["district"],
                "state": entry["state"],
                "mandal": entry["mandal"],
                "latitude": entry["latitude"],
                "longitude": entry["longitude"],
                "lat": entry["latitude"],
                "lng": entry["longitude"],
                "is_exact": False,
            }

        return None

    @classmethod
    def lookup_pincode(cls, pincode: str) -> dict[str, Any] | None:
        return cls.lookup(pincode)
