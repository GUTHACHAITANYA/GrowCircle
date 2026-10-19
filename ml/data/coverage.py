"""
GrowCircle Mandi & Crop Historical Coverage Analyzer (Phase ML-0).
Analyzes trading series per mandi and crop:
- Days available, missing days, coverage percentage
- Total gaps, longest consecutive gap (days)
- Honest sufficiency gate: flags which crops and mandis have enough history
  to model vs which lack data and MUST NOT be modeled.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# Strict modeling sufficiency criteria
MIN_DAYS_AVAILABLE = 180       # Minimum 6 months of observations
MIN_COVERAGE_PCT = 60.0        # Minimum 60% coverage across the date span
MAX_PERMISSIBLE_GAP = 21       # No gap exceeding 3 consecutive weeks (21 days)


def analyze_mandi_crop_coverage(df: pd.DataFrame) -> list[dict[str, Any]]:
    """
    Computes coverage metrics for each (crop_id, mandi_id) pair.
    Returns sorted list of coverage summary dictionaries.
    """
    df = df.copy()
    df["price_date"] = pd.to_datetime(df["price_date"]).dt.date

    # Mandi metadata lookup
    mandi_meta: dict[str, dict[str, str]] = {
        "ap-guntur-01": {"name": "Guntur", "district": "Guntur"},
        "ap-madanapalle-01": {"name": "Madanapalle", "district": "Annamayya"},
        "ap-vijayawada-01": {"name": "Vijayawada", "district": "NTR"},
        "ap-kurnool-01": {"name": "Kurnool", "district": "Kurnool"},
        "ap-anantapur-01": {"name": "Anantapur", "district": "Anantapur"},
        "ap-tirupati-01": {"name": "Tirupati", "district": "Tirupati"},
    }

    results: list[dict[str, Any]] = []

    grouped = df.groupby(["crop_id", "mandi_id"])

    for (crop_id, mandi_id), group in grouped:
        dates = sorted(group["price_date"].unique())
        if not dates:
            continue

        start_date = dates[0]
        end_date = dates[-1]
        total_span = (end_date - start_date).days + 1
        days_avail = len(dates)
        missing_days = total_span - days_avail
        coverage_pct = round((days_avail / total_span) * 100.0, 2) if total_span > 0 else 0.0

        # Compute gaps in consecutive calendar days
        gaps: list[int] = []
        for i in range(1, len(dates)):
            gap = (dates[i] - dates[i - 1]).days - 1
            if gap > 0:
                gaps.append(gap)

        longest_gap = max(gaps) if gaps else 0
        total_gaps = len(gaps)
        avg_gap = round(sum(gaps) / len(gaps), 2) if gaps else 0.0

        # Sufficiency evaluation
        disqualifiers: list[str] = []
        if days_avail < MIN_DAYS_AVAILABLE:
            disqualifiers.append(f"Insufficient observations ({days_avail} < {MIN_DAYS_AVAILABLE} min)")
        if coverage_pct < MIN_COVERAGE_PCT:
            disqualifiers.append(f"Low density ({coverage_pct}% < {MIN_COVERAGE_PCT}% min)")
        if longest_gap > MAX_PERMISSIBLE_GAP:
            disqualifiers.append(f"Severe gap outage ({longest_gap} days > {MAX_PERMISSIBLE_GAP} max)")

        sufficient = len(disqualifiers) == 0
        status = "SUFFICIENT (MODEL)" if sufficient else "INSUFFICIENT (DO NOT MODEL)"

        meta = mandi_meta.get(str(mandi_id), {"name": str(mandi_id), "district": "Unknown"})

        results.append({
            "crop_id": crop_id,
            "mandi_id": mandi_id,
            "mandi_name": meta["name"],
            "district": meta["district"],
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_span_days": total_span,
            "days_available": days_avail,
            "missing_days": missing_days,
            "coverage_pct": coverage_pct,
            "total_gaps": total_gaps,
            "longest_gap_days": longest_gap,
            "avg_gap_days": avg_gap,
            "sufficient_for_modeling": sufficient,
            "status": status,
            "disqualifiers": disqualifiers,
        })

    # Sort: sufficient first, then by crop and coverage descending
    results.sort(key=lambda x: (not x["sufficient_for_modeling"], x["crop_id"], -x["coverage_pct"]))
    return results


def generate_coverage_markdown_table(coverage_list: list[dict[str, Any]]) -> str:
    """Renders formatted GitHub markdown tables for the data report."""
    lines: list[str] = [
        "| Crop | Mandi | District | Span | Days Present | Coverage % | Longest Gap | Modeling Status | Action |",
        "| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |",
    ]

    for r in coverage_list:
        action = "Proceed with features & backtest" if r["sufficient_for_modeling"] else f"REJECT: {'; '.join(r['disqualifiers'])}"
        status_badge = "**ELIGIBLE**" if r["sufficient_for_modeling"] else "*DISQUALIFIED*"
        lines.append(
            f"| `{r['crop_id']}` | **{r['mandi_name']}** | {r['district']} | "
            f"{r['total_span_days']}d | {r['days_available']} | {r['coverage_pct']}% | "
            f"{r['longest_gap_days']}d | {status_badge} | {action} |"
        )

    return "\n".join(lines)


if __name__ == "__main__":
    csv_file = Path("data/processed/cleaned_mandi_prices.csv")
    if not csv_file.exists():
        print("Cleaned prices CSV not found. Run cleaning first.")
    else:
        df = pd.read_csv(csv_file)
        res = analyze_mandi_crop_coverage(df)
        print(generate_coverage_markdown_table(res))
