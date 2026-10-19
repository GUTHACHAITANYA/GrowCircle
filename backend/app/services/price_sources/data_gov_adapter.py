"""
data.gov.in Agmarknet Price Source Adapter.
Connects to Open Government Data (OGD) Platform India:
Resource: 'Current Daily Price of Various Commodities from Various Markets (Mandi)' (9ef84268-d588-465a-a308-a864a43d0070).
"""

import json
import logging
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx

from backend.app.core.config import settings
from backend.app.services.price_sources.base import NormalizedPriceRecord, PriceSource

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
RAW_DATA_DIR = ROOT_DIR / "data" / "raw" / "data_gov_in"


class DataGovInAdapter(PriceSource):
    BASE_URL = "https://api.data.gov.in/resource"
    DEFAULT_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"

    @property
    def source_name(self) -> str:
        return "data.gov.in"

    @property
    def priority(self) -> int:
        return 2

    def _parse_date(self, raw_date: str) -> date:
        """Parses Agmarknet arrival date formatted as DD/MM/YYYY or YYYY-MM-DD."""
        clean = raw_date.strip().replace("\\", "")
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(clean, fmt).date()
            except ValueError:
                continue
        return datetime.now(UTC).date()

    def _save_raw_payload(self, records: list[dict[str, Any]], target_date: date) -> str:
        """Saves untouched raw payload to data/raw/data_gov_in/YYYY-MM-DD/ for auditability."""
        date_folder = RAW_DATA_DIR / target_date.isoformat()
        date_folder.mkdir(parents=True, exist_ok=True)
        timestamp_str = datetime.now(UTC).strftime("%H%M%S")
        file_path = date_folder / f"raw_fetch_{timestamp_str}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        return str(file_path.relative_to(ROOT_DIR))

    async def fetch_prices(
        self,
        state: str | None = None,
        commodity: str | None = None,
        district: str | None = None,
        target_date: date | None = None,
    ) -> list[NormalizedPriceRecord]:
        api_key = settings.DATA_GOV_API_KEY
        resource_id = settings.DATA_GOV_RESOURCE_ID or self.DEFAULT_RESOURCE_ID
        query_date = target_date or datetime.now(UTC).date()

        if not api_key:
            if settings.APP_MODE == "production":
                logger.error("DATA_GOV_API_KEY is unset in production mode. Refusing to fetch.")
                return []
            logger.info("DATA_GOV_API_KEY is unset in demo mode. Checking sandbox fixtures.")
            mock_file = ROOT_DIR / "backend" / "data" / "sample_ap_banana.json"
            if mock_file.exists():
                with open(mock_file, encoding="utf-8") as f:
                    raw_records = json.load(f)
                    return self._normalize_records(raw_records, raw_ref="demo_fixture")
            return []

        url = f"{self.BASE_URL}/{resource_id}"
        params: dict[str, Any] = {
            "api-key": api_key,
            "format": "json",
            "limit": 500,
        }
        if state:
            params["filters[state.keyword]"] = state
        if commodity:
            params["filters[commodity.keyword]"] = commodity
        if district:
            params["filters[district]"] = district

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GrowCircle/1.0 (Agriculture Open Price Engine)",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_records = data.get("records", [])
                    if raw_records:
                        raw_ref = self._save_raw_payload(raw_records, query_date)
                        logger.info(
                            f"Fetched {len(raw_records)} live records from data.gov.in ({raw_ref})."
                        )
                        return self._normalize_records(raw_records, raw_ref=raw_ref)
                logger.warning(
                    f"data.gov.in returned HTTP {resp.status_code}: {resp.text[:200]}"
                )
        except Exception as ex:
            logger.error(f"Error fetching from data.gov.in: {ex}")

        # In production mode: FAIL CLOSED. Return empty list.
        if settings.APP_MODE == "production":
            return []

        # In demo mode only: Fallback to verified local sample
        mock_file = ROOT_DIR / "backend" / "data" / "sample_ap_banana.json"
        if mock_file.exists():
            with open(mock_file, encoding="utf-8") as f:
                raw_records = json.load(f)
                return self._normalize_records(raw_records, raw_ref="demo_fixture")
        return []

    def _normalize_records(
        self, records: list[dict[str, Any]], raw_ref: str
    ) -> list[NormalizedPriceRecord]:
        normalized: list[NormalizedPriceRecord] = []
        fetched_at = datetime.now(UTC)

        for r in records:
            try:
                rep_date = self._parse_date(str(r.get("arrival_date", "")))
                min_p = float(r.get("min_price", 0.0))
                max_p = float(r.get("max_price", 0.0))
                modal_p = float(r.get("modal_price", 0.0))

                rec = NormalizedPriceRecord(
                    state=str(r.get("state", "Andhra Pradesh")).strip(),
                    district=str(r.get("district", "Unknown")).strip(),
                    mandi=str(r.get("market", "")).strip(),
                    commodity=str(r.get("commodity", "")).strip(),
                    variety=str(r.get("variety", "Other")).strip(),
                    grade=str(r.get("grade", "FAQ")).strip(),
                    reported_date=rep_date,
                    min_price=min_p,
                    max_price=max_p,
                    modal_price=modal_p,
                    unit="quintal",
                    source_name="data.gov.in",
                    raw_data=r,
                    fetched_at=fetched_at,
                )
                normalized.append(rec)
            except Exception as ex:
                logger.warning(f"Skipping malformed record {r}: {ex}")

        return normalized
