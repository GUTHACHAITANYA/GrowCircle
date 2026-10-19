"""
Official Agmarknet Portal CSV Importer Adapter (Priority 1).
Parses standard CSV exports downloaded directly from the official https://agmarknet.gov.in portal.
Stores untouched raw CSV files in data/raw/agmarknet_portal/YYYY-MM-DD/.
"""

import csv
import io
import logging
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from backend.app.services.price_sources.base import NormalizedPriceRecord, PriceSource

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
RAW_DATA_DIR = ROOT_DIR / "data" / "raw" / "agmarknet_portal"


class AgmarknetPortalCsvAdapter(PriceSource):
    def __init__(self, storage_dir: str | None = None):
        self.raw_data_dir = Path(storage_dir) if storage_dir else RAW_DATA_DIR

    @property
    def source_name(self) -> str:
        return "agmarknet_portal_csv"

    @property
    def priority(self) -> int:
        return 1  # Highest priority: official manual portal download

    def _parse_date(self, date_str: str) -> date:
        clean = date_str.strip()
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d-%b-%Y"):
            try:
                return datetime.strptime(clean, fmt).date()
            except ValueError:
                continue
        return datetime.now(UTC).date()

    def save_raw_csv(self, content_bytes: bytes, target_date: date) -> str:
        """Saves raw untouched portal CSV file for auditing and compliance."""
        date_folder = self.raw_data_dir / target_date.isoformat()
        date_folder.mkdir(parents=True, exist_ok=True)
        timestamp_str = datetime.now(UTC).strftime("%H%M%S")
        file_path = date_folder / f"agmarknet_portal_{timestamp_str}.csv"
        with open(file_path, "wb") as f:
            f.write(content_bytes)
        try:
            return str(file_path.relative_to(ROOT_DIR))
        except ValueError:
            return str(file_path)

    def parse_csv_file(self, file_path: str) -> list[NormalizedPriceRecord]:
        """Reads CSV file from disk, backs up raw copy, and parses records."""
        path = Path(file_path)
        content_bytes = path.read_bytes()
        raw_ref = self.save_raw_csv(content_bytes, date.today())
        return self.parse_csv_content(content_bytes.decode("utf-8-sig"), raw_ref=raw_ref)

    def parse_csv_content(
        self, csv_text: str, raw_ref: str | None = None
    ) -> list[NormalizedPriceRecord]:
        """Parses CSV text content into normalized price records."""
        f = io.StringIO(csv_text.strip())
        reader = csv.DictReader(f)
        normalized: list[NormalizedPriceRecord] = []
        fetched_at = datetime.now(UTC)

        for row in reader:
            # Handle potential key variations from different Agmarknet portal report exports
            clean_row = {k.strip().lower().replace(" ", "_"): v.strip() for k, v in row.items() if k}
            state = clean_row.get("state") or clean_row.get("state_name", "Andhra Pradesh")
            district = clean_row.get("district") or clean_row.get("district_name", "Unknown")
            market = clean_row.get("market") or clean_row.get("market_name", clean_row.get("mandi", ""))
            commodity = clean_row.get("commodity") or clean_row.get("commodity_name", "")
            variety = clean_row.get("variety", "Other")
            grade = clean_row.get("grade", "FAQ")
            arr_date_str = clean_row.get("arrival_date") or clean_row.get("price_date") or clean_row.get("date", "")

            try:
                rep_date = self._parse_date(arr_date_str)
                min_p = float(clean_row.get("min_price", 0.0) or 0.0)
                max_p = float(clean_row.get("max_price", 0.0) or 0.0)
                modal_p = float(clean_row.get("modal_price", 0.0) or 0.0)

                rec = NormalizedPriceRecord(
                    state=state,
                    district=district,
                    mandi=market,
                    commodity=commodity,
                    variety=variety,
                    grade=grade,
                    reported_date=rep_date,
                    min_price=min_p,
                    max_price=max_p,
                    modal_price=modal_p,
                    unit="quintal",
                    source_name="agmarknet_portal_csv",
                    raw_data={**row, "_raw_payload_ref": raw_ref or ""},
                    fetched_at=fetched_at,
                )
                normalized.append(rec)
            except Exception as ex:
                logger.warning(f"Error parsing Agmarknet CSV row {row}: {ex}")

        return normalized

    async def fetch_prices(
        self,
        state: str | None = None,
        commodity: str | None = None,
        district: str | None = None,
        target_date: date | None = None,
    ) -> list[NormalizedPriceRecord]:
        """Loads and parses any pending CSV files dropped in data/raw/agmarknet_portal/."""
        records: list[NormalizedPriceRecord] = []
        if not RAW_DATA_DIR.exists():
            return records

        for csv_path in RAW_DATA_DIR.glob("**/*.csv"):
            try:
                with open(csv_path, encoding="utf-8-sig") as f:
                    content = f.read()
                    parsed = self.parse_csv_content(content, raw_ref=str(csv_path.relative_to(ROOT_DIR)))
                    records.extend(parsed)
            except Exception as ex:
                logger.error(f"Error reading local portal CSV {csv_path}: {ex}")

        return records
