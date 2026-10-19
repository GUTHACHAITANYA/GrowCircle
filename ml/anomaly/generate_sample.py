"""
Curated Ground-Truth Hand-Labelled Sample Generator for Anomaly Detection (Phase ML-2).
Generates a representative dataset (data/anomaly_evaluation_sample.csv) of 250 records
with human ground-truth labels across prices, deals, and reporting drops.
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

SAMPLE_FILE = Path("data/anomaly_evaluation_sample.csv")


def generate_curated_sample() -> None:
    SAMPLE_FILE.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    row_id = 1

    # -------------------------------------------------------------
    # 1. Clean Mandi Prices (130 rows) -> Ground Truth Anomaly = 0
    # -------------------------------------------------------------
    crops_clean = [
        ("banana", "ap-guntur-01", 20.0, 30.0, 25.0, 15.0),
        ("banana", "ap-vijayawada-01", 22.0, 32.0, 26.5, 12.0),
        ("tomato", "ap-madanapalle-01", 12.0, 22.0, 18.0, 45.0),
        ("onion", "ap-kurnool-01", 18.0, 28.0, 22.0, 80.0),
        ("potato", "ap-kurnool-01", 16.0, 24.0, 20.0, 35.0),
    ]

    for crop, mandi, min_p, max_p, modal, arr in crops_clean:
        for day in range(1, 27):
            d = date(2026, 8, day)
            # Add minor daily fluctuation (+- 5%)
            jitter = ((day % 5) - 2) * 0.5
            rows.append({
                "sample_id": f"SMP-{row_id:04d}",
                "category": "price",
                "entity_id": f"PRC-{row_id:05d}",
                "crop_id": crop,
                "mandi_id": mandi,
                "price_date": d.isoformat(),
                "min_price_kg": round(min_p + jitter, 2),
                "max_price_kg": round(max_p + jitter, 2),
                "modal_price_kg": round(modal + jitter, 2),
                "arrival_tonnes": round(arr + (day % 3), 1),
                "is_ground_truth_anomaly": 0,
                "expected_reason": "CLEAN",
                "notes": "Regular market trading within standard historical bounds",
            })
            row_id += 1

    # -------------------------------------------------------------
    # 2. Price Unit Errors (25 rows) -> Ground Truth Anomaly = 1
    # -------------------------------------------------------------
    unit_error_examples = [
        ("banana", "ap-guntur-01", 2500.0, 3500.0, 3000.0, "Agmarknet quintal price entered in kg field"),
        ("tomato", "ap-madanapalle-01", 1800.0, 2800.0, 2200.0, "Raw quintal unit confusion"),
        ("onion", "ap-kurnool-01", 2000.0, 3000.0, 2500.0, "Mandi clerk typed quintal without conversion"),
        ("potato", "ap-kurnool-01", 1500.0, 2500.0, 2000.0, "Quintal entered in kg rate column"),
        ("banana", "ap-vijayawada-01", 2800.0, 3800.0, 3200.0, "Quintal entered directly"),
    ]
    for crop, mandi, min_p, max_p, modal, note in unit_error_examples:
        for idx in range(5):
            rows.append({
                "sample_id": f"SMP-{row_id:04d}",
                "category": "price",
                "entity_id": f"PRC-{row_id:05d}",
                "crop_id": crop,
                "mandi_id": mandi,
                "price_date": date(2026, 9, 1 + idx).isoformat(),
                "min_price_kg": min_p + idx * 50,
                "max_price_kg": max_p + idx * 50,
                "modal_price_kg": modal + idx * 50,
                "arrival_tonnes": 20.0,
                "is_ground_truth_anomaly": 1,
                "expected_reason": "RULE_UNIT_ERROR",
                "notes": note,
            })
            row_id += 1

    # -------------------------------------------------------------
    # 3. Price 10x Typos & Extreme Jumps (20 rows) -> Ground Truth Anomaly = 1
    # -------------------------------------------------------------
    ten_x_examples = [
        ("banana", "ap-guntur-01", 240.0, 280.0, 260.0, "Typo: extra zero added (260 vs normal 26)"),
        ("tomato", "ap-madanapalle-01", 180.0, 220.0, 200.0, "Typo: extra zero added (200 vs normal 20)"),
        ("onion", "ap-kurnool-01", 2.1, 2.5, 2.2, "Typo: decimal point error (2.2 vs normal 22)"),
        ("potato", "ap-kurnool-01", 1.8, 2.4, 2.0, "Typo: decimal point error (2.0 vs normal 20)"),
    ]
    for crop, mandi, min_p, max_p, modal, note in ten_x_examples:
        for idx in range(5):
            rows.append({
                "sample_id": f"SMP-{row_id:04d}",
                "category": "price",
                "entity_id": f"PRC-{row_id:05d}",
                "crop_id": crop,
                "mandi_id": mandi,
                "price_date": date(2026, 9, 7 + idx).isoformat(),
                "min_price_kg": min_p,
                "max_price_kg": max_p,
                "modal_price_kg": modal,
                "arrival_tonnes": 25.0,
                "is_ground_truth_anomaly": 1,
                "expected_reason": "RULE_10X_SPIKE" if modal > 50 else "RULE_10X_CRASH",
                "notes": note,
            })
            row_id += 1

    # -------------------------------------------------------------
    # 4. Inverted Bounds & Non-Positive Prices (15 rows) -> Ground Truth Anomaly = 1
    # -------------------------------------------------------------
    invalid_bounds = [
        ("banana", "ap-guntur-01", 35.0, 20.0, 25.0, "RULE_INVERTED_RANGE", "min_price > max_price inverted bounds"),
        ("tomato", "ap-madanapalle-01", -5.0, 25.0, 15.0, "RULE_NEGATIVE_OR_ZERO", "Negative min price recorded"),
        ("onion", "ap-kurnool-01", 20.0, 30.0, 35.0, "RULE_MODAL_OUT_OF_BOUNDS", "Modal price exceeds max_price"),
    ]
    for crop, mandi, min_p, max_p, modal, reason, note in invalid_bounds:
        for idx in range(5):
            rows.append({
                "sample_id": f"SMP-{row_id:04d}",
                "category": "price",
                "entity_id": f"PRC-{row_id:05d}",
                "crop_id": crop,
                "mandi_id": mandi,
                "price_date": date(2026, 9, 13 + idx).isoformat(),
                "min_price_kg": min_p,
                "max_price_kg": max_p,
                "modal_price_kg": modal,
                "arrival_tonnes": 15.0,
                "is_ground_truth_anomaly": 1,
                "expected_reason": reason,
                "notes": note,
            })
            row_id += 1

    # -------------------------------------------------------------
    # 5. Statistical Residual Anomalies (20 rows) -> Ground Truth Anomaly = 1
    # -------------------------------------------------------------
    stat_anomalies = [
        ("tomato", "ap-madanapalle-01", 45.0, 55.0, 50.0, "Sudden massive uncorroborated single-mandi spike (normal 18)"),
        ("onion", "ap-kurnool-01", 55.0, 68.0, 62.0, "Sudden uncorroborated single-mandi surge (normal 22)"),
        ("banana", "ap-guntur-01", 8.0, 12.0, 10.0, "Sudden severe uncorroborated crash without arrival surge"),
        ("potato", "ap-kurnool-01", 45.0, 55.0, 50.0, "Sudden unprovoked price spike with Z > 4.5"),
    ]
    for crop, mandi, min_p, max_p, modal, note in stat_anomalies:
        for idx in range(5):
            rows.append({
                "sample_id": f"SMP-{row_id:04d}",
                "category": "price",
                "entity_id": f"PRC-{row_id:05d}",
                "crop_id": crop,
                "mandi_id": mandi,
                "price_date": date(2026, 9, 19 + idx).isoformat(),
                "min_price_kg": min_p,
                "max_price_kg": max_p,
                "modal_price_kg": modal,
                "arrival_tonnes": 12.0,
                "is_ground_truth_anomaly": 1,
                "expected_reason": "STAT_RESIDUAL_ZSCORE",
                "notes": note,
            })
            row_id += 1

    # -------------------------------------------------------------
    # 6. Legitimate Corroborated Market Swings (10 rows) -> Ground Truth Anomaly = 0 (Auto-Cleared)
    # -------------------------------------------------------------
    for idx in range(10):
        rows.append({
            "sample_id": f"SMP-{row_id:04d}",
            "category": "price",
            "entity_id": f"PRC-{row_id:05d}",
            "crop_id": "tomato",
            "mandi_id": "ap-madanapalle-01",
            "price_date": date(2026, 9, 25 + (idx % 5)).isoformat(),
            "min_price_kg": 28.0,
            "max_price_kg": 38.0,
            "modal_price_kg": 34.0,
            "arrival_tonnes": 5.0,  # Supply drop
            "is_ground_truth_anomaly": 0,
            "expected_reason": "CLEAN",
            "notes": "Regional price swing confirmed by neighboring Chittoor/Tirupati mandis following rains",
        })
        row_id += 1

    # -------------------------------------------------------------
    # 7. Deal Anomalies (15 rows: 10 anomalies, 5 clean)
    # -------------------------------------------------------------
    # 5 Clean offers
    for _idx in range(5):
        rows.append({
            "sample_id": f"SMP-{row_id:04d}",
            "category": "deal",
            "entity_id": f"OFFER-{row_id:04d}",
            "crop_id": "banana",
            "mandi_id": "ap-guntur-01",
            "offered_price_kg": 26.0,
            "mandi_benchmark_price_kg": 25.0,
            "cancelled_count": 0,
            "total_interactions": 10,
            "is_photo_reuse": 0,
            "is_ground_truth_anomaly": 0,
            "expected_reason": "CLEAN",
            "notes": "Fair deal offer within 4% of mandi price",
        })
        row_id += 1

    # 4 Extreme lowball offers (Anomaly = 1)
    for _idx in range(4):
        rows.append({
            "sample_id": f"SMP-{row_id:04d}",
            "category": "deal",
            "entity_id": f"OFFER-{row_id:04d}",
            "crop_id": "tomato",
            "mandi_id": "ap-madanapalle-01",
            "offered_price_kg": 7.0,  # 65% lowball
            "mandi_benchmark_price_kg": 20.0,
            "cancelled_count": 0,
            "total_interactions": 5,
            "is_photo_reuse": 0,
            "is_ground_truth_anomaly": 1,
            "expected_reason": "DEAL_OFFER_EXTREME_LOWBALL",
            "notes": "Predatory lowball offer 65% below mandi benchmark",
        })
        row_id += 1

    # 3 Serial Cancellers (Anomaly = 1)
    for _idx in range(3):
        rows.append({
            "sample_id": f"SMP-{row_id:04d}",
            "category": "deal",
            "entity_id": f"OFFER-{row_id:04d}",
            "crop_id": "onion",
            "mandi_id": "ap-kurnool-01",
            "offered_price_kg": 22.0,
            "mandi_benchmark_price_kg": 22.0,
            "cancelled_count": 4,
            "total_interactions": 5,  # 80% cancellation
            "is_photo_reuse": 0,
            "is_ground_truth_anomaly": 1,
            "expected_reason": "DEAL_SERIAL_CANCELLATIONS",
            "notes": "Buyer with 80% cancellation rate in last 7 days",
        })
        row_id += 1

    # 3 Suspicious Photo Reuse (Anomaly = 1)
    for _idx in range(3):
        rows.append({
            "sample_id": f"SMP-{row_id:04d}",
            "category": "deal",
            "entity_id": f"LST-{row_id:04d}",
            "crop_id": "banana",
            "mandi_id": "ap-guntur-01",
            "offered_price_kg": 25.0,
            "mandi_benchmark_price_kg": 25.0,
            "cancelled_count": 0,
            "total_interactions": 2,
            "is_photo_reuse": 1,
            "is_ground_truth_anomaly": 1,
            "expected_reason": "DEAL_STOLEN_PHOTO_REUSE",
            "notes": "Listing reused exact photo hash from another farmer's lot",
        })
        row_id += 1

    # -------------------------------------------------------------
    # 8. Reporting Drop Scenarios (15 rows: 10 clean, 5 outages)
    # -------------------------------------------------------------
    # 7 Normal weekdays (Anomaly = 0)
    for idx in range(7):
        rows.append({
            "sample_id": f"SMP-{row_id:04d}",
            "category": "reporting_drop",
            "entity_id": f"RPT-{row_id:04d}",
            "target_date": date(2026, 10, 1 + idx).isoformat(),
            "actual_reporting_mandis": 19,
            "expected_reporting_mandis": 18.5,
            "is_ground_truth_anomaly": 0,
            "expected_reason": "CLEAN",
            "notes": "Normal weekday reporting operations",
        })
        row_id += 1

    # 3 Normal Sunday Low Volume (Anomaly = 0)
    for idx in range(3):
        rows.append({
            "sample_id": f"SMP-{row_id:04d}",
            "category": "reporting_drop",
            "entity_id": f"RPT-{row_id:04d}",
            "target_date": date(2026, 10, 4 + idx * 7).isoformat(),  # Sundays
            "actual_reporting_mandis": 2,
            "expected_reporting_mandis": 2.0,
            "is_ground_truth_anomaly": 0,
            "expected_reason": "CLEAN",
            "notes": "Normal Sunday market closure, expected low reporting",
        })
        row_id += 1

    # 5 Catastrophic Upstream Outages (Anomaly = 1)
    for idx in range(5):
        rows.append({
            "sample_id": f"SMP-{row_id:04d}",
            "category": "reporting_drop",
            "entity_id": f"RPT-{row_id:04d}",
            "target_date": date(2026, 10, 15 + idx).isoformat(),  # Weekday outage
            "actual_reporting_mandis": 2,  # Severe drop from 18.5
            "expected_reporting_mandis": 18.5,
            "is_ground_truth_anomaly": 1,
            "expected_reason": "CRITICAL_OUTAGE",
            "notes": "Catastrophic drop to 2 reporting mandis on a weekday (data.gov.in outage)",
        })
        row_id += 1

    # Write CSV
    fieldnames = [
        "sample_id",
        "category",
        "entity_id",
        "crop_id",
        "mandi_id",
        "price_date",
        "min_price_kg",
        "max_price_kg",
        "modal_price_kg",
        "arrival_tonnes",
        "offered_price_kg",
        "mandi_benchmark_price_kg",
        "cancelled_count",
        "total_interactions",
        "is_photo_reuse",
        "target_date",
        "actual_reporting_mandis",
        "expected_reporting_mandis",
        "is_ground_truth_anomaly",
        "expected_reason",
        "notes",
    ]

    with open(SAMPLE_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} curated hand-labelled records in {SAMPLE_FILE}")


if __name__ == "__main__":
    generate_curated_sample()
