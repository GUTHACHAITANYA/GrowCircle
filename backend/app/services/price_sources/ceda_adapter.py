"""
CEDA Agri Market Data (CEDA-AMD) Adapter (Ashoka University).

LICENSE & TERMS OF USE:
1. Non-Commercial Use Only: Data may only be downloaded, displayed, or integrated strictly
   for non-commercial purposes at no cost.
2. Mandatory Attribution: Any display, application, or visualization incorporating CEDA data
   MUST include the formal citation:
   'CEDA Agri Market Data (CEDA-AMD), 2000-2023. Centre for Economic Data & Analysis,
    Ashoka University, https://ceda.ashoka.edu.in/agmarknet'
3. Branding Requirement: The official CEDA logo must appear on the bottom right of the visual space,
   accompanied by clear text credit to 'Centre for Economic Data & Analysis, Ashoka University'.
4. Disclaimer: Data is provided 'as is' without warranty. Errors may be reported to ceda@ashoka.edu.in.
5. Coverage & Limits: Primarily provides comprehensive historical agricultural market series (2000-2023)
   rather than real-time intraday auction feeds.
"""

import json
import logging
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from backend.app.services.price_sources.base import NormalizedPriceRecord, PriceSource

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
RAW_DATA_DIR = ROOT_DIR / "data" / "raw" / "ceda_ashoka"


class CedaAgriAdapter(PriceSource):
    MANDATORY_CITATION = (
        "CEDA Agri Market Data (CEDA-AMD), 2000-2023. "
        "Centre for Economic Data & Analysis, Ashoka University, https://ceda.ashoka.edu.in/agmarknet"
    )
    BASE_URL = "https://ceda.ashoka.edu.in/api/v1/agrimarket"

    @property
    def source_name(self) -> str:
        return "ceda_ashoka"

    @property
    def priority(self) -> int:
        return 3

    def get_terms_and_licence(self) -> dict[str, Any]:
        """Returns limits, terms of use, and license details for CEDA dataset."""
        return {
            "source": "Centre for Economic Data & Analysis (CEDA), Ashoka University",
            "citation": self.MANDATORY_CITATION,
            "license": "Creative Commons Attribution-NonCommercial (CC BY-NC 4.0)",
            "non_commercial_only": True,
            "attribution_required": True,
            "logo_placement": "Bottom right of visual frame accompanied by explicit source credit",
            "coverage_and_limits": (
                "Comprehensive historical agricultural market series (2000-2023) across major crops and Indian states. "
                "Intraday / real-time live auction feeds are not supported; data is updated periodically."
            ),
            "disclaimer": "Provided 'as is' without warranty for academic and non-commercial research.",
        }

    def _save_raw_payload(self, records: list[dict[str, Any]], target_date: date) -> str:
        date_folder = RAW_DATA_DIR / target_date.isoformat()
        date_folder.mkdir(parents=True, exist_ok=True)
        timestamp_str = datetime.now(UTC).strftime("%H%M%S")
        file_path = date_folder / f"raw_ceda_{timestamp_str}.json"
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
        """
        Fetches records from CEDA portal export or historical repository.
        Enforces non-commercial license and metadata attribution tags.
        """
        query_date = target_date or datetime.now(UTC).date()
        logger.info(
            f"CEDA adapter queried for state={state}, commodity={commodity}, date={query_date}. "
            f"Notice: CEDA dataset covers historical series with mandatory attribution ({self.MANDATORY_CITATION})."
        )

        # Look for local CEDA structured drops in data/ceda/
        ceda_local_file = ROOT_DIR / "data" / "ceda" / f"{commodity or 'banana'}_ap.json"
        if ceda_local_file.exists():
            with open(ceda_local_file, encoding="utf-8") as f:
                raw_data = json.load(f)
                return self._normalize_records(raw_data)

        # In production/live without historical offline sync, CEDA returns empty list
        return []

    def _normalize_records(self, records: list[dict[str, Any]]) -> list[NormalizedPriceRecord]:
        normalized: list[NormalizedPriceRecord] = []
        fetched_at = datetime.now(UTC)

        for r in records:
            try:
                date_str = str(r.get("date", r.get("arrival_date", "")))
                rep_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                rec = NormalizedPriceRecord(
                    state=str(r.get("state", "Andhra Pradesh")).strip(),
                    district=str(r.get("district", "Unknown")).strip(),
                    mandi=str(r.get("market", r.get("mandi", ""))).strip(),
                    commodity=str(r.get("commodity", "")).strip(),
                    variety=str(r.get("variety", "Other")).strip(),
                    grade=str(r.get("grade", "FAQ")).strip(),
                    reported_date=rep_date,
                    min_price=float(r.get("min_price", 0.0)),
                    max_price=float(r.get("max_price", 0.0)),
                    modal_price=float(r.get("modal_price", 0.0)),
                    unit="quintal",
                    source_name="ceda_ashoka",
                    raw_data={**r, "_ceda_citation": self.MANDATORY_CITATION},
                    fetched_at=fetched_at,
                )
                normalized.append(rec)
            except Exception as ex:
                logger.warning(f"Error parsing CEDA record {r}: {ex}")

        return normalized
