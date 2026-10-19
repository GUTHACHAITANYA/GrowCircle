"""
Agronomic Knowledge Base & Cost-of-Cultivation Norms (Phase ML-3).
Verified against:
1. Acharya N.G. Ranga Agricultural University (ANGRAU) Agro-Climatic Zone Guidelines.
2. ICAR Krishi Vigyan Kendra (KVK) District Contingency Crop Plans.
3. State Level Bankers' Committee (SLBC) Andhra Pradesh - Scale of Finance 2024-2026.
4. Department of Horticulture & Directorate of Economics and Statistics (DES), AP.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CropAgronomyProfile:
    crop_id: str
    crop_name_en: str
    category: str
    duration_months: int
    # NABARD / SLBC Scale of Finance cost per acre (₹ / acre)
    cost_per_acre_p10: float
    cost_per_acre_p50: float
    cost_per_acre_p90: float
    # Yield per acre (tonnes / acre)
    yield_tonnes_p10: float
    yield_tonnes_p50: float
    yield_tonnes_p90: float
    # Perishability index (1=dry grain/storage, 5=highly perishable day-to-day)
    perishability_score: int
    suitable_districts: list[str]
    # Suitable planting months: 1=Jan, 2=Feb, ..., 12=Dec
    suitable_planting_months: list[int]
    agronomic_source: str
    finance_source: str
    variety_recommendations: list[str]


# Verified ANGRAU / KVK / SLBC crop agronomic profiles for Andhra Pradesh
AGRONOMIC_PROFILES: dict[str, CropAgronomyProfile] = {
    "banana": CropAgronomyProfile(
        crop_id="banana",
        crop_name_en="Banana",
        category="fruit",
        duration_months=11,
        cost_per_acre_p10=72000.0,
        cost_per_acre_p50=88000.0,
        cost_per_acre_p90=108000.0,
        yield_tonnes_p10=22.0,
        yield_tonnes_p50=30.0,
        yield_tonnes_p90=38.0,
        perishability_score=3,
        suitable_districts=["guntur", "ntr", "krishna", "annamayya", "chittoor"],
        suitable_planting_months=[6, 7, 8, 9, 10, 11, 12],  # Kharif and Late Kharif / Rabi planting
        agronomic_source="ANGRAU Coastal & Rayalaseema Zone Horticultural Guide; KVK Lam Guntur",
        finance_source="SLBC AP Scale of Finance 2024-2026 (Tissue Culture Banana with Drip)",
        variety_recommendations=["Grand Naine", "Robusta", "Karpura", "Amruthapani"],
    ),
    "tomato": CropAgronomyProfile(
        crop_id="tomato",
        crop_name_en="Tomato",
        category="vegetable",
        duration_months=3,
        cost_per_acre_p10=38000.0,
        cost_per_acre_p50=52000.0,
        cost_per_acre_p90=68000.0,
        yield_tonnes_p10=11.0,
        yield_tonnes_p50=16.0,
        yield_tonnes_p90=22.0,
        perishability_score=5,  # Highly perishable, extreme crash vulnerability
        suitable_districts=["annamayya", "chittoor", "kurnool", "guntur", "ntr"],
        suitable_planting_months=[1, 2, 5, 6, 7, 8, 9, 10, 11],  # Rabi, Kharif, Summer
        agronomic_source="ANGRAU Rayalaseema & Scarce Rainfall Zone Guide; KVK Kalikiri Annamayya",
        finance_source="SLBC AP Scale of Finance 2024-2026 (Staked Hybrid Tomato)",
        variety_recommendations=["Arka Rakshak", "US 440", "Abhinav", "Saaho"],
    ),
    "onion": CropAgronomyProfile(
        crop_id="onion",
        crop_name_en="Onion",
        category="vegetable",
        duration_months=4,
        cost_per_acre_p10=34000.0,
        cost_per_acre_p50=46000.0,
        cost_per_acre_p90=58000.0,
        yield_tonnes_p10=6.5,
        yield_tonnes_p50=10.0,
        yield_tonnes_p90=14.0,
        perishability_score=2,  # Medium storage potential
        suitable_districts=["kurnool", "guntur", "annamayya"],
        suitable_planting_months=[6, 7, 8, 9, 10, 11],  # Kharif and Rabi
        agronomic_source="ANGRAU Scarce Rainfall Zone Package; KVK Yagantipalle Kurnool",
        finance_source="SLBC AP Scale of Finance 2024-2026 (Bulb Onion Irrigated)",
        variety_recommendations=["Kurnool Local Red", "Bhima Super", "Agrifound Light Red"],
    ),
    "potato": CropAgronomyProfile(
        crop_id="potato",
        crop_name_en="Potato",
        category="vegetable",
        duration_months=3,
        cost_per_acre_p10=40000.0,
        cost_per_acre_p50=54000.0,
        cost_per_acre_p90=66000.0,
        yield_tonnes_p10=6.0,
        yield_tonnes_p50=9.0,
        yield_tonnes_p90=12.5,
        perishability_score=2,
        suitable_districts=["kurnool", "annamayya"],
        suitable_planting_months=[10, 11, 12],  # Winter / Rabi only in AP
        agronomic_source="ANGRAU Horticulture Research Station Chintapalle & KVK Kurnool",
        finance_source="SLBC AP Scale of Finance 2024-2026 (Commercial Table Potato)",
        variety_recommendations=["Kufri Jyoti", "Kufri Pukhraj", "Kufri Surya"],
    ),
    "chilli": CropAgronomyProfile(
        crop_id="chilli",
        crop_name_en="Green Chilli",
        category="vegetable",
        duration_months=5,
        cost_per_acre_p10=46000.0,
        cost_per_acre_p50=62000.0,
        cost_per_acre_p90=78000.0,
        yield_tonnes_p10=5.5,
        yield_tonnes_p50=8.5,
        yield_tonnes_p90=12.0,
        perishability_score=3,
        suitable_districts=["guntur", "ntr", "krishna", "kurnool"],
        suitable_planting_months=[7, 8, 9, 10],  # Kharif / Early Rabi
        agronomic_source="ANGRAU Regional Agricultural Research Station (RARS) Lam, Guntur",
        finance_source="SLBC AP Scale of Finance 2024-2026 (Hybrid Chilli Irrigated)",
        variety_recommendations=["Guntur Sannam (LCA 334)", "LCA 206", "Teja"],
    ),
    "groundnut": CropAgronomyProfile(
        crop_id="groundnut",
        crop_name_en="Groundnut",
        category="oilseed",
        duration_months=4,
        cost_per_acre_p10=22000.0,
        cost_per_acre_p50=30000.0,
        cost_per_acre_p90=38000.0,
        yield_tonnes_p10=0.8,
        yield_tonnes_p50=1.4,
        yield_tonnes_p90=2.0,
        perishability_score=1,  # Low perishability / dry storage
        suitable_districts=["annamayya", "chittoor", "kurnool"],
        suitable_planting_months=[6, 7, 11, 12],  # Kharif rainfed & Rabi irrigated
        agronomic_source="ANGRAU Agricultural Research Station Kadiri; KVK Kalikiri",
        finance_source="SLBC AP Scale of Finance 2024-2026 (Groundnut Pods)",
        variety_recommendations=["Kadiri 6", "Kadiri 9", "TMV 2", "Dharani"],
    ),
    "maize": CropAgronomyProfile(
        crop_id="maize",
        crop_name_en="Maize",
        category="cereal",
        duration_months=4,
        cost_per_acre_p10=24000.0,
        cost_per_acre_p50=32000.0,
        cost_per_acre_p90=42000.0,
        yield_tonnes_p10=2.2,
        yield_tonnes_p50=3.2,
        yield_tonnes_p90=4.2,
        perishability_score=1,
        suitable_districts=["guntur", "kurnool", "ntr"],
        suitable_planting_months=[6, 7, 10, 11, 12],  # Kharif & Rabi
        agronomic_source="ANGRAU Maize Research Station; KVK Lam Guntur",
        finance_source="SLBC AP Scale of Finance 2024-2026 (Hybrid Maize)",
        variety_recommendations=["DHM 117", "DKC 9108", "Pioneer 3396"],
    ),
}


def get_agronomically_suitable_crops(
    district: str,
    planting_month: int,
) -> list[CropAgronomyProfile]:
    """
    Returns candidate crops verified suitable by ANGRAU / KVK
    for the specific district and planting month.
    """
    d_clean = district.lower().replace("-", " ").strip()
    suitable = []

    for profile in AGRONOMIC_PROFILES.values():
        if any(d in d_clean for d in profile.suitable_districts):
            if planting_month in profile.suitable_planting_months:
                suitable.append(profile)

    return suitable
