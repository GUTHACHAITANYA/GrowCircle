"""
Price Reconciler & Data Quality Guard for Multi-Source Ingestion.
Enforces:
1. Strict priority ordering (agmarknet_portal_csv > data.gov.in > ceda_ashoka).
2. Data quality gates (non-positive, min > max, modal out of range, 10x spikes, invalid units).
3. Cross-source discrepancy flagging (>15% divergence) with official source selection.
4. Retention of original units & conversion to kg / ton at display time.
"""

import logging
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.app.models.crop import Crop
from backend.app.models.mandi import Mandi
from backend.app.models.price import Price
from backend.app.services.price_sources.base import NormalizedPriceRecord

logger = logging.getLogger(__name__)

SOURCE_PRIORITY: dict[str, int] = {
    "agmarknet_portal_csv": 1,
    "data.gov.in": 2,
    "ceda_ashoka": 3,
    "manual": 4,
    "demo": 99,
}

DISCREPANCY_THRESHOLD_PCT = 0.15  # 15% difference triggers review flag


class PriceReconciler:
    def __init__(self, db: Session):
        self.db = db

    def validate_quality(
        self, record: NormalizedPriceRecord, prev_modal_quintal: float | None = None
    ) -> tuple[str, str | None]:
        """
        Validates individual record against mathematical and agricultural bounds.
        Returns: (anomaly_status, error_reason)
        """
        # 1. Negative or zero values
        if record.min_price <= 0 or record.max_price <= 0 or record.modal_price <= 0:
            return "quarantined_negative", f"Non-positive price detected: min={record.min_price}, max={record.max_price}, modal={record.modal_price}"

        # 2. Min > Max
        if record.min_price > record.max_price:
            return "quarantined_min_gt_max", f"Min price ({record.min_price}) exceeds max price ({record.max_price})"

        # 3. Modal outside [min, max]
        if record.modal_price < record.min_price or record.modal_price > record.max_price:
            return "quarantined_modal_range", f"Modal price ({record.modal_price}) outside range [{record.min_price}, {record.max_price}]"

        # 4. Unexpected units
        clean_unit = record.unit.strip().lower()
        if clean_unit not in ("quintal", "kg", "ton", "tonne"):
            return "quarantined_unit", f"Unrecognized commodity unit: '{record.unit}'"

        # 5. 10x jump check from previous modal price
        if prev_modal_quintal and prev_modal_quintal > 0:
            # Standardize record.modal_price to quintal for comparison
            curr_quintal = self._to_quintal(record.modal_price, record.unit)
            ratio = curr_quintal / prev_modal_quintal
            if ratio >= 10.0 or ratio <= 0.1:
                return "quarantined_10x_spike", f"10x anomaly spike detected: {curr_quintal:.1f} vs prev {prev_modal_quintal:.1f} (ratio={ratio:.2f})"

        return "clean", None

    def _to_quintal(self, val: float, unit: str) -> float:
        u = unit.strip().lower()
        if u == "kg":
            return val * 100.0
        if u in ("ton", "tonne"):
            return val * 10.0
        return val

    def reconcile_and_save(
        self, records: list[NormalizedPriceRecord]
    ) -> dict[str, int]:
        """
        Reconciles normalized price records across sources and saves to database.
        Returns statistics dictionary (ingested, quarantined, updated, rejected).
        """
        stats = {
            "total_received": len(records),
            "clean_saved": 0,
            "quarantined": 0,
            "discrepancies": 0,
        }

        # Group records by compound entity key: (mandi_name, commodity, variety, grade, reported_date)
        grouped: dict[tuple[str, str, str, str, date], list[NormalizedPriceRecord]] = {}
        for r in records:
            group_key = (
                r.mandi.strip().lower(),
                r.commodity.strip().lower(),
                r.variety.strip().lower(),
                r.grade.strip().lower(),
                r.reported_date,
            )
            grouped.setdefault(group_key, []).append(r)

        for group_key, group_records in grouped.items():
            mandi_name, commodity, variety, grade, rep_date = group_key

            # Find or create Mandi
            sample_rec = group_records[0]
            mandi = self.db.scalar(
                select(Mandi).where(Mandi.name.ilike(sample_rec.mandi))
            )
            if not mandi:
                # Create mandi if new
                mandi = Mandi(
                    name=sample_rec.mandi,
                    district=sample_rec.district,
                    state=sample_rec.state,
                )
                self.db.add(mandi)
                self.db.flush()

            # Ensure crop exists
            crop_id = commodity.lower().replace(" ", "-")
            crop = self.db.scalar(select(Crop).where(Crop.id == crop_id))
            if not crop:
                crop = Crop(
                    id=crop_id,
                    name_en=sample_rec.commodity.capitalize(),
                    name_te=sample_rec.commodity,
                    name_hi=sample_rec.commodity,
                    name_gu=sample_rec.commodity,
                    category="fruit" if "banana" in crop_id else "produce",
                )
                self.db.add(crop)
                self.db.flush()

            # Retrieve latest previous clean price for 10x jump check
            prev_price = self.db.scalar(
                select(Price)
                .where(
                    Price.mandi_id == mandi.id,
                    Price.crop_id == crop.id,
                    Price.price_date < rep_date,
                    Price.anomaly_status == "clean",
                )
                .order_by(desc(Price.price_date))
                .limit(1)
            )
            prev_modal = prev_price.modal_price_quintal if prev_price else None

            # Sort group records by priority (1 is highest priority)
            group_records.sort(key=lambda rec: SOURCE_PRIORITY.get(rec.source_name, 50))

            primary_rec = group_records[0]
            discrepancy_flag = False

            # Check cross-source discrepancy if multiple sources reported
            if len(group_records) > 1:
                p1_modal_q = self._to_quintal(primary_rec.modal_price, primary_rec.unit)
                for other_rec in group_records[1:]:
                    other_modal_q = self._to_quintal(other_rec.modal_price, other_rec.unit)
                    diff_pct = abs(p1_modal_q - other_modal_q) / max(p1_modal_q, other_modal_q)
                    if diff_pct > DISCREPANCY_THRESHOLD_PCT:
                        discrepancy_flag = True
                        stats["discrepancies"] += 1
                        logger.warning(
                            f"Price discrepancy between {primary_rec.source_name} (₹{p1_modal_q}/q) and "
                            f"{other_rec.source_name} (₹{other_modal_q}/q) for {mandi.name} - {crop.id} on {rep_date} "
                            f"(diff={diff_pct:.1%}). Flagging for review."
                        )

            # Persist each source record into database
            for idx, rec in enumerate(group_records):
                is_primary = (idx == 0)
                status, reason = self.validate_quality(rec, prev_modal)

                if status == "clean" and discrepancy_flag and not is_primary:
                    status = "source_discrepancy"

                # Standardize units
                min_q = self._to_quintal(rec.min_price, rec.unit)
                max_q = self._to_quintal(rec.max_price, rec.unit)
                modal_q = self._to_quintal(rec.modal_price, rec.unit)

                min_kg = round(min_q / 100.0, 2)
                max_kg = round(max_q / 100.0, 2)
                modal_kg = round(modal_q / 100.0, 2)
                modal_ton = round(modal_q * 10.0, 2)

                # Check if exact row exists
                existing = self.db.scalar(
                    select(Price).where(
                        Price.mandi_id == mandi.id,
                        Price.crop_id == crop.id,
                        Price.variety == rec.variety,
                        Price.grade == rec.grade,
                        Price.price_date == rec.reported_date,
                        Price.source == rec.source_name,
                    )
                )

                raw_ref = rec.raw_data.get("_raw_payload_ref", "")

                if existing:
                    existing.min_price_quintal = min_q
                    existing.max_price_quintal = max_q
                    existing.modal_price_quintal = modal_q
                    existing.min_price_kg = min_kg
                    existing.max_price_kg = max_kg
                    existing.modal_price_kg = modal_kg
                    existing.modal_price_ton = modal_ton
                    existing.original_unit = rec.unit
                    existing.original_min_price = rec.min_price
                    existing.original_max_price = rec.max_price
                    existing.original_modal_price = rec.modal_price
                    existing.anomaly_status = status
                    existing.raw_payload_ref = raw_ref or existing.raw_payload_ref
                    existing.fetched_at = rec.fetched_at
                else:
                    new_p = Price(
                        mandi_id=mandi.id,
                        crop_id=crop.id,
                        variety=rec.variety,
                        grade=rec.grade,
                        price_date=rec.reported_date,
                        min_price_quintal=min_q,
                        max_price_quintal=max_q,
                        modal_price_quintal=modal_q,
                        min_price_kg=min_kg,
                        max_price_kg=max_kg,
                        modal_price_kg=modal_kg,
                        modal_price_ton=modal_ton,
                        original_unit=rec.unit,
                        original_min_price=rec.min_price,
                        original_max_price=rec.max_price,
                        original_modal_price=rec.modal_price,
                        arrival_tonnes=float(rec.raw_data.get("arrival_tonnes", 0.0) or 0.0),
                        anomaly_status=status,
                        source=rec.source_name,
                        raw_payload_ref=raw_ref,
                        fetched_at=rec.fetched_at,
                    )
                    self.db.add(new_p)

                if status == "clean":
                    stats["clean_saved"] += 1
                else:
                    stats["quarantined"] += 1

        self.db.commit()
        return stats
