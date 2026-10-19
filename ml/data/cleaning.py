"""
GrowCircle ML Mandi Price Cleaning Pipeline (Phase ML-0).
Applies documented, deterministic data hygiene rules:
1. Unit fixes (₹/quintal -> ₹/kg, metric tonnes)
2. Duplicate resolution (prioritize highest arrival volume)
3. Variety normalisation (canonical APMC taxonomy)
4. Outlier flags (FLAG AND KEEP, NEVER SILENTLY DELETE)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

DATA_RAW_DIR = Path("data/raw")
DATA_PROCESSED_DIR = Path("data/processed")

# Canonical variety normalization lookup
VARIETY_ALIASES: dict[str, dict[str, str]] = {
    "banana": {
        "amritapani": "Amruthapani",
        "amruthapani": "Amruthapani",
        "robusta": "Robusta",
        "cavendish": "Robusta",
        "karpura": "Karpura",
        "chakkara keli": "Chakkara Keli",
        "grand naine": "Grand Naine",
        "local": "Other",
    },
    "tomato": {
        "hybrid": "Hybrid",
        "hybrid tomato": "Hybrid",
        "desi": "Desi",
        "desi tomato": "Desi",
        "local tomato": "Desi",
        "pahuja": "Pahuja",
        "sahu": "Hybrid",
    },
    "onion": {
        "red": "Red",
        "red onion": "Red",
        "white": "White",
        "white onion": "White",
        "bellary": "Bellary",
        "nasik": "Nasik",
        "small onion": "Red",
    },
    "potato": {
        "jyoti": "Jyoti",
        "kufri": "Kufri",
        "kufri badshah": "Kufri",
        "desi": "Desi",
        "chipsona": "Chipsona",
        "pahari": "Jyoti",
    },
}

# Domain bounds for outlier flagging (₹ / kg)
CROP_PRICE_BOUNDS: dict[str, dict[str, float]] = {
    "banana": {"min_kg": 2.0, "max_kg": 150.0},
    "tomato": {"min_kg": 1.5, "max_kg": 180.0},
    "onion": {"min_kg": 2.0, "max_kg": 120.0},
    "potato": {"min_kg": 2.0, "max_kg": 90.0},
}


class CleaningPipeline:
    """Deterministic cleaning pipeline for raw historical mandi prices."""

    @classmethod
    def clean_records(cls, raw_records: list[dict[str, Any]]) -> tuple[pd.DataFrame, dict[str, Any]]:
        """
        Cleans a list of raw Agmarknet dictionaries.
        Returns (cleaned_dataframe, cleaning_metrics).
        """
        if not raw_records:
            return pd.DataFrame(), {"error": "Empty input"}

        df = pd.DataFrame(raw_records)
        raw_count = len(df)
        metrics: dict[str, Any] = {
            "raw_rows": raw_count,
            "unit_fixes_applied": 0,
            "duplicates_removed": 0,
            "varieties_normalized": 0,
            "outliers_flagged": 0,
        }

        # 1. Column Standardization & Unit Fixes
        # Agmarknet raw units: ₹ / quintal. 1 quintal = 100 kg.
        df["price_date"] = pd.to_datetime(df["arrival_date"]).dt.date
        df["crop_id"] = df["crop_id"].str.lower()
        df["mandi_id"] = df["mandi_id"].astype(str)

        # Fix numeric types
        df["min_price_quintal"] = pd.to_numeric(df["min_price"], errors="coerce").fillna(0.0)
        df["max_price_quintal"] = pd.to_numeric(df["max_price"], errors="coerce").fillna(0.0)
        df["modal_price_quintal"] = pd.to_numeric(df["modal_price"], errors="coerce").fillna(0.0)
        df["arrival_tonnes"] = pd.to_numeric(df.get("arrival_tonnes", 0.0), errors="coerce").fillna(0.0)

        # Standard units (₹ / kg and ₹ / ton)
        df["min_price_kg"] = (df["min_price_quintal"] / 100.0).round(2)
        df["max_price_kg"] = (df["max_price_quintal"] / 100.0).round(2)
        df["modal_price_kg"] = (df["modal_price_quintal"] / 100.0).round(2)
        df["modal_price_ton"] = (df["modal_price_kg"] * 1000.0).round(2)
        metrics["unit_fixes_applied"] = raw_count

        # 2. Variety Normalisation
        def normalize_variety(row: pd.Series) -> str:
            crop = row["crop_id"]
            var_raw = str(row.get("variety", "Other")).strip()
            var_clean = var_raw.lower()
            if crop in VARIETY_ALIASES and var_clean in VARIETY_ALIASES[crop]:
                return VARIETY_ALIASES[crop][var_clean]
            return var_raw.capitalize() if var_raw else "Other"

        orig_varieties = df["variety"].copy()
        df["variety"] = df.apply(normalize_variety, axis=1)
        normalized_count = int((orig_varieties != df["variety"]).sum())
        metrics["varieties_normalized"] = normalized_count

        # Ensure Grade is standard
        df["grade"] = df.get("grade", "FAQ").fillna("FAQ").astype(str).str.upper()

        # 3. Duplicate Removal
        # Key: (mandi_id, crop_id, price_date, variety, grade)
        # Sort by arrival_tonnes descending to keep highest volume record on tie
        df = df.sort_values(by=["arrival_tonnes"], ascending=False)
        subset_keys = ["mandi_id", "crop_id", "price_date", "variety", "grade"]
        duplicates_mask = df.duplicated(subset=subset_keys, keep="first")
        duplicates_count = int(duplicates_mask.sum())
        df = df[~duplicates_mask].copy()
        metrics["duplicates_removed"] = duplicates_count

        # Sort chronologically by date and mandi
        df = df.sort_values(by=["price_date", "mandi_id"]).reset_index(drop=True)

        # 4. Outlier Flags: FLAG AND KEEP, NEVER SILENTLY DELETE
        df["is_outlier"] = False
        df["outlier_reason"] = ""

        outlier_flags: list[bool] = []
        outlier_reasons: list[str] = []

        for _, row in df.iterrows():
            is_outlier = False
            reasons: list[str] = []
            crop = row["crop_id"]
            modal = row["modal_price_kg"]
            min_p = row["min_price_kg"]
            max_p = row["max_price_kg"]

            # Hierarchy check
            if min_p > max_p:
                is_outlier = True
                reasons.append("min_greater_than_max")
            if modal < min_p or modal > max_p:
                is_outlier = True
                reasons.append("modal_outside_min_max")

            # Domain floor and ceiling bounds
            bounds = CROP_PRICE_BOUNDS.get(crop, {"min_kg": 1.0, "max_kg": 200.0})
            if modal < bounds["min_kg"]:
                is_outlier = True
                reasons.append(f"below_floor_{bounds['min_kg']}")
            elif modal > bounds["max_kg"]:
                is_outlier = True
                reasons.append(f"above_ceiling_{bounds['max_kg']}")

            # Non-positive values
            if modal <= 0 or min_p <= 0 or max_p <= 0:
                is_outlier = True
                reasons.append("non_positive_price")

            outlier_flags.append(is_outlier)
            outlier_reasons.append(", ".join(reasons) if reasons else "clean")

        df["is_outlier"] = outlier_flags
        df["outlier_reason"] = outlier_reasons
        metrics["outliers_flagged"] = int(df["is_outlier"].sum())
        metrics["clean_rows_kept"] = len(df)

        return df, metrics

    @classmethod
    def clean_all_raw_files(cls) -> tuple[pd.DataFrame, dict[str, Any]]:
        """
        Reads all raw crop JSON files from `data/raw/`, cleans them,
        and saves processed outputs to `data/processed/cleaned_mandi_prices.csv`.
        """
        DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        all_raw_records: list[dict[str, Any]] = []

        raw_files = list(DATA_RAW_DIR.glob("ap_*.json"))
        if not raw_files:
            raise FileNotFoundError("No raw APMC data found in data/raw/. Run backfill first.")

        for f in raw_files:
            with open(f, encoding="utf-8") as fp:
                recs = json.load(fp)
                all_raw_records.extend(recs)

        df, metrics = cls.clean_records(all_raw_records)

        # Save to processed CSV
        out_csv = DATA_PROCESSED_DIR / "cleaned_mandi_prices.csv"
        df.to_csv(out_csv, index=False)
        metrics["output_csv"] = str(out_csv)

        logger.info(
            f"[CLEANING COMPLETE] {metrics['raw_rows']} raw rows -> "
            f"{metrics['clean_rows_kept']} kept. "
            f"Duplicates: {metrics['duplicates_removed']}, "
            f"Normalized: {metrics['varieties_normalized']}, "
            f"Outliers flagged (kept): {metrics['outliers_flagged']}"
        )
        return df, metrics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cleaned_df, report = CleaningPipeline.clean_all_raw_files()
    print(json.dumps(report, indent=2))
