"""
GrowCircle Dataset Versioning & Registry Convention (Phase ML-0).
Follows standard ML dataset registry convention:
- name: Dataset identifier
- version: Semantic versioning
- data_hash: SHA-256 content cryptographic hash
- metrics: Volume, coverage, quality pass rate
- owner: Engineering team / entity
- date: Registration timestamp

Provides DVC-compatible metadata files (`.dvc`) and central JSON catalog.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

REGISTRY_FILE = Path("ml/data/dataset_registry.json")
PROCESSED_DATA_PATH = Path("data/processed/cleaned_mandi_prices.csv")
DVC_META_PATH = Path("data/processed/cleaned_mandi_prices.csv.dvc")


def compute_file_sha256(filepath: Path) -> str:
    """Calculates SHA-256 checksum of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class DatasetRegistry:
    """Manages versioned dataset registrations and DVC sidecar descriptors."""

    @classmethod
    def register_dataset(
        cls,
        name: str = "ap_mandi_prices_historical",
        version: str = "1.0.0",
        owner: str = "GrowCircle ML Team",
        data_path: Path = PROCESSED_DATA_PATH,
    ) -> dict[str, Any]:
        """
        Registers a processed dataset and produces DVC-equivalent descriptor.
        """
        if not data_path.exists():
            raise FileNotFoundError(f"Dataset file not found at {data_path}")

        # Compute SHA-256
        data_hash = compute_file_sha256(data_path)
        file_size_bytes = data_path.stat().st_size

        df = pd.read_csv(data_path)
        dates = pd.to_datetime(df["price_date"]).dt.date

        # Compute dataset metrics
        metrics = {
            "total_rows": len(df),
            "file_size_kb": round(file_size_bytes / 1024.0, 2),
            "date_range": f"{dates.min()} to {dates.max()}",
            "crops_count": int(df["crop_id"].nunique()),
            "crops": sorted(df["crop_id"].unique().tolist()),
            "mandis_count": int(df["mandi_id"].nunique()),
            "mandis": sorted(df["mandi_id"].unique().tolist()),
            "outliers_flagged": int(df["is_outlier"].sum()) if "is_outlier" in df.columns else 0,
            "outlier_rate_pct": round(float(df["is_outlier"].mean()) * 100.0, 3) if "is_outlier" in df.columns else 0.0,
        }

        entry: dict[str, Any] = {
            "name": name,
            "version": version,
            "data_hash": f"sha256:{data_hash}",
            "metrics": metrics,
            "owner": owner,
            "date": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "file_path": str(data_path),
        }

        # 1. Update Registry Catalog (ml/data/dataset_registry.json)
        catalog: dict[str, Any] = {"datasets": []}
        if REGISTRY_FILE.exists():
            try:
                with open(REGISTRY_FILE, encoding="utf-8") as f:
                    catalog = json.load(f)
            except Exception:
                catalog = {"datasets": []}

        # Replace or append version
        catalog["datasets"] = [
            d for d in catalog.get("datasets", [])
            if not (d.get("name") == name and d.get("version") == version)
        ]
        catalog["datasets"].append(entry)

        REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2)

        # 2. Write DVC-compatible sidecar file
        dvc_content = (
            f"schema: 2.0\n"
            f"outs:\n"
            f"  - path: {data_path.name}\n"
            f"    size: {file_size_bytes}\n"
            f"    hash: sha256:{data_hash}\n"
            f"meta:\n"
            f"  name: {name}\n"
            f"  version: {version}\n"
            f"  owner: {owner}\n"
            f"  registered_date: {entry['date']}\n"
            f"  total_rows: {metrics['total_rows']}\n"
        )
        with open(DVC_META_PATH, "w", encoding="utf-8") as f:
            f.write(dvc_content)

        logger.info(f"[DATASET REGISTERED] {name}:{version} (Hash: {data_hash[:12]}...)")
        return entry


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    reg = DatasetRegistry.register_dataset()
    print(json.dumps(reg, indent=2))
