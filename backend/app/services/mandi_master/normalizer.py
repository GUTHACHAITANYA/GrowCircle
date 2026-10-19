"""
Mandi Name Normalizer and Duplicate Detection Engine.
Cleans raw market names (stripping APMC, Market Yard, Rythu Bazar, etc.)
and identifies duplicates and spelling variations across mandi records.
"""

import re
from difflib import SequenceMatcher
from typing import Any

NOISE_PATTERNS = [
    r"\ba\.?p\.?m\.?c\.?(?:\b|$|\s)",
    r"\bmarket\s+yard\b",
    r"\bsub[\s\-]?yard\b",
    r"\brythu\s+bazar\b",
    r"\brythu\s+bazaar\b",
    r"\bfruit\s+market\b",
    r"\bveg(etable)?\s+market\b",
    r"\bgrain\s+market\b",
    r"\bkisan\s+bazar\b",
    r"\bmarket\b",
    r"\bmandi\b",
    r"\byard\b",
]

# Canonical corrections for known spelling discrepancies in AP & neighbouring states
KNOWN_SPELLING_CORRECTIONS = {
    "vijaywada": "Vijayawada",
    "bezawada": "Vijayawada",
    "madanapalli": "Madanapalle",
    "rajahmundri": "Rajahmundry",
    "rajamahendravaram": "Rajahmundry",
    "tirupathi": "Tirupati",
    "ananthapur": "Anantapur",
    "ananthapuram": "Anantapur",
    "kurnoolu": "Kurnool",
    "kurnool": "Kurnool",
    "visakhapatnam": "Visakhapatnam",
    "vizag": "Visakhapatnam",
    "santhamaguluru": "Santhamaguluru",
    "santhamagulur": "Santhamaguluru",
    "somala": "Somala",
}


def normalize_market_name(raw_name: str) -> str:
    """
    Cleans raw mandi name by removing APMC/Market Yard suffixes, parenthetical tags,
    extra whitespace, and harmonizing known spelling variants.
    """
    if not raw_name:
        return ""

    text = raw_name.strip()

    # 1. Remove parenthetical notes like (F&V), (Sub-Yard), (Grain), etc.
    text = re.sub(r"\(.*?\)", "", text)

    # 2. Strip noise phrases case-insensitively
    for pattern in NOISE_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # 3. Clean punctuation and multiple spaces
    text = re.sub(r"[,/\\_\-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # 4. Check known spelling corrections
    lower_clean = text.lower()
    if lower_clean in KNOWN_SPELLING_CORRECTIONS:
        return KNOWN_SPELLING_CORRECTIONS[lower_clean]

    # 5. Title case formatting
    return text.title()


def string_similarity(a: str, b: str) -> float:
    """Computes string similarity score between 0.0 and 1.0."""
    return SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio()


def find_potential_duplicates(
    mandis_data: list[dict[str, Any]], threshold: float = 0.85
) -> list[dict[str, Any]]:
    """
    Scans a collection of mandi records and detects duplicates based on
    canonical name identity or high string similarity within the same district/state.
    """
    duplicates = []
    n = len(mandis_data)

    for i in range(n):
        for j in range(i + 1, n):
            m1 = mandis_data[i]
            m2 = mandis_data[j]

            # Compare only within same state (or same district for higher confidence)
            same_state = (m1.get("state", "").strip().lower() == m2.get("state", "").strip().lower())
            if not same_state:
                continue

            name1_norm = m1.get("canonical_name") or normalize_market_name(m1.get("name", ""))
            name2_norm = m2.get("canonical_name") or normalize_market_name(m2.get("name", ""))

            # Direct canonical match
            if name1_norm.lower() == name2_norm.lower():
                duplicates.append({
                    "mandi_1_id": m1.get("id"),
                    "mandi_1_name": m1.get("name"),
                    "mandi_2_id": m2.get("id"),
                    "mandi_2_name": m2.get("name"),
                    "canonical_name": name1_norm,
                    "district": m1.get("district"),
                    "similarity": 1.0,
                    "reason": "Exact canonical name match",
                })
                continue

            # Fuzzy similarity
            sim = string_similarity(name1_norm, name2_norm)
            if sim >= threshold:
                duplicates.append({
                    "mandi_1_id": m1.get("id"),
                    "mandi_1_name": m1.get("name"),
                    "mandi_2_id": m2.get("id"),
                    "mandi_2_name": m2.get("name"),
                    "canonical_name": f"{name1_norm} / {name2_norm}",
                    "district": m1.get("district"),
                    "similarity": round(sim, 3),
                    "reason": f"High fuzzy similarity ({sim:.2f}) in {m1.get('district')}",
                })

    return duplicates
