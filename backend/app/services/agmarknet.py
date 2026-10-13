"""
Agmarknet daily price fetcher and ingestion pipeline.
Pulls prices from data.gov.in (or sandbox mock fallback) and upserts them cleanly.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.crop import Crop
from backend.app.models.ingestion import IngestionLog
from backend.app.models.mandi import Mandi
from backend.app.models.price import Price
from backend.app.services.data_quality import DataQualityGuard, quintal_to_kg, quintal_to_ton

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


class AgmarknetService:
    BASE_URL = "https://api.data.gov.in/resource"

    @classmethod
    async def fetch_ap_banana_raw(cls) -> list[dict[str, Any]]:
        """
        Fetches Banana records for Andhra Pradesh from data.gov.in.
        Falls back to verified sandbox dataset if API key is unset or network error occurs.
        """
        if settings.DATA_GOV_API_KEY:
            url = f"{cls.BASE_URL}/{settings.DATA_GOV_RESOURCE_ID}"
            params = {
                "api-key": settings.DATA_GOV_API_KEY,
                "format": "json",
                "filters[state.keyword]": "Andhra Pradesh",
                "filters[commodity.keyword]": "Banana",
                "limit": 100,
            }
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url, params=params)
                    if resp.status_code == 200:
                        data = resp.json()
                        records = data.get("records", [])
                        if records:
                            logger.info(
                                f"Successfully fetched {len(records)} records from data.gov.in"
                            )
                            return records
                    logger.warning(
                        f"data.gov.in returned status {resp.status_code}. Using sandbox data."
                    )
            except Exception as e:
                logger.warning(
                    f"Network error accessing data.gov.in: {e}. Falling back to sandbox data."
                )

        # Sandbox / Mock Fallback
        mock_file = DATA_DIR / "sample_ap_banana.json"
        if mock_file.exists():
            with open(mock_file, encoding="utf-8") as f:
                records = json.load(f)
                logger.info(f"Loaded {len(records)} verified sandbox Banana records for AP.")
                return records
        return []

    @classmethod
    def ingest_records(cls, db: Session, raw_records: list[dict[str, Any]]) -> IngestionLog:
        """
        Validates, normalizes, and upserts raw records into the database.
        Returns an IngestionLog record detailing the outcome.
        """
        # Ensure 'banana' crop row exists
        crop = db.scalar(select(Crop).where(Crop.id == "banana"))
        if not crop:
            crop = Crop(
                id="banana",
                name_en="Banana",
                name_te="అరటిపండు",
                name_hi="केला",
                name_gu="કેળા",
                icon="banana",
                category="fruit",
            )
            db.add(crop)
            db.flush()

        fetched_count = len(raw_records)
        upserted_count = 0
        failed_count = 0
        error_messages: list[str] = []

        # Load coordinate overrides if available
        coords_map = cls._load_coords_override()

        for rec in raw_records:
            # 1. Data Quality Guard Validation
            is_valid, reason = DataQualityGuard.validate_price_record(rec)
            if not is_valid:
                failed_count += 1
                error_messages.append(f"Rejected record {rec.get('market')}: {reason}")
                logger.warning(f"Data quality rejection: {reason} | Record: {rec}")
                continue

            try:
                # 2. Find or Create Mandi
                market_name = str(rec["market"]).strip()
                district_name = str(rec.get("district", "Unknown")).strip()
                state_name = str(rec.get("state", "Andhra Pradesh")).strip()

                mandi = db.scalar(
                    select(Mandi).where(
                        Mandi.name == market_name,
                        Mandi.district == district_name,
                        Mandi.state == state_name,
                    )
                )

                if not mandi:
                    # Determine coordinates
                    lat, lng = coords_map.get(market_name, (None, None))
                    geom = None
                    if lat is not None and lng is not None:
                        geom = from_shape(Point(lng, lat), srid=4326)

                    mandi = Mandi(
                        name=market_name,
                        district=district_name,
                        state=state_name,
                        latitude=lat,
                        longitude=lng,
                        location=geom,
                    )
                    db.add(mandi)
                    db.flush()

                # 3. Parse date and prices
                date_str = str(rec["arrival_date"]).strip()
                # Handle formats 'YYYY-MM-DD' or 'DD/MM/YYYY'
                if "/" in date_str:
                    price_date = datetime.strptime(date_str, "%d/%m/%Y").date()
                else:
                    price_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                min_quintal = float(rec["min_price"])
                max_quintal = float(rec["max_price"])
                modal_quintal = float(rec["modal_price"])

                variety = str(rec.get("variety", "Robusta")).strip()
                grade = str(rec.get("grade", "FAQ")).strip()
                arrival_tonnes = float(rec.get("arrival_tonnes", 0.0))

                # Unit Conversions
                min_kg = quintal_to_kg(min_quintal)
                max_kg = quintal_to_kg(max_quintal)
                modal_kg = quintal_to_kg(modal_quintal)
                modal_ton = quintal_to_ton(modal_quintal)

                # 4. Upsert Price Record
                existing_price = db.scalar(
                    select(Price).where(
                        Price.mandi_id == mandi.id,
                        Price.crop_id == "banana",
                        Price.variety == variety,
                        Price.grade == grade,
                        Price.price_date == price_date,
                    )
                )

                if existing_price:
                    existing_price.min_price_quintal = min_quintal
                    existing_price.max_price_quintal = max_quintal
                    existing_price.modal_price_quintal = modal_quintal
                    existing_price.min_price_kg = min_kg
                    existing_price.max_price_kg = max_kg
                    existing_price.modal_price_kg = modal_kg
                    existing_price.modal_price_ton = modal_ton
                    existing_price.arrival_tonnes = arrival_tonnes
                    existing_price.source = "data.gov.in"
                else:
                    new_price = Price(
                        mandi_id=mandi.id,
                        crop_id="banana",
                        variety=variety,
                        grade=grade,
                        price_date=price_date,
                        min_price_quintal=min_quintal,
                        max_price_quintal=max_quintal,
                        modal_price_quintal=modal_quintal,
                        min_price_kg=min_kg,
                        max_price_kg=max_kg,
                        modal_price_kg=modal_kg,
                        modal_price_ton=modal_ton,
                        arrival_tonnes=arrival_tonnes,
                        source="data.gov.in",
                    )
                    db.add(new_price)

                upserted_count += 1

            except Exception as ex:
                failed_count += 1
                error_messages.append(f"Database error on {rec.get('market')}: {ex}")
                logger.exception("Error during price record upsert")

        # Create Ingestion Log
        status = (
            "success" if failed_count == 0 else "stale_warning" if upserted_count > 0 else "failure"
        )
        log = IngestionLog(
            source="data.gov.in",
            records_fetched=fetched_count,
            records_upserted=upserted_count,
            records_failed=failed_count,
            status=status,
            error_message="; ".join(error_messages[:5]) if error_messages else None,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def _load_coords_override() -> dict[str, tuple[float, float]]:
        coords: dict[str, tuple[float, float]] = {}
        csv_path = DATA_DIR / "mandi_coordinates_override.csv"
        if csv_path.exists():
            with open(csv_path, encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split(",")
                    if len(parts) >= 5 and parts[0] != "name":
                        try:
                            coords[parts[0]] = (float(parts[3]), float(parts[4]))
                        except ValueError:
                            pass
        return coords
