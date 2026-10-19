"""
Deal and Marketplace Anomaly Detector (Phase ML-2).
Monitors negotiation integrity:
1. Offers diverging excessively from prevailing mandi spot price.
2. Serial / frequent cancellations indicating bad-faith negotiation.
3. Suspicious photo reuse across produce listings (violating fresh-lot capture rule).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DealAnomalyResult:
    is_anomaly: bool
    reason_code: str
    severity: str  # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'NONE'
    anomaly_type: str  # 'offer_price', 'cancellations', 'photo_reuse', 'clean'
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_anomaly": self.is_anomaly,
            "reason_code": self.reason_code,
            "severity": self.severity,
            "anomaly_type": self.anomaly_type,
            "details": self.details,
        }


class DealAnomalyDetector:
    """
    Detects market manipulation, negotiation fraud, and physical verification breaches.
    """

    def __init__(self) -> None:
        # In-memory photo hash registry: {hash: {"farmer_id": id, "listing_id": id, "created_at": date}}
        self._photo_hash_registry: dict[str, dict[str, Any]] = {}

    def register_listing_photos(
        self,
        listing_id: int,
        farmer_id: int,
        photo_hashes: list[str],
        created_at: date,
    ) -> None:
        """Registers verified photo hashes to detect subsequent reuse."""
        for ph in photo_hashes:
            if ph:
                self._photo_hash_registry[ph] = {
                    "listing_id": listing_id,
                    "farmer_id": farmer_id,
                    "created_at": created_at,
                }

    def evaluate_offer_price(
        self,
        offered_price_kg: float,
        mandi_benchmark_price_kg: float,
        crop_id: str,
        listing_expected_price_kg: float | None = None,
    ) -> DealAnomalyResult:
        """
        Flags offers deviating excessively (>40%) from current mandi spot prices.
        """
        if mandi_benchmark_price_kg <= 0 or offered_price_kg <= 0:
            return DealAnomalyResult(
                is_anomaly=True,
                reason_code="DEAL_INVALID_PRICE_VALUE",
                severity="CRITICAL",
                anomaly_type="offer_price",
                details={"offered_price_kg": offered_price_kg, "benchmark": mandi_benchmark_price_kg},
            )

        pct_deviation = abs(offered_price_kg - mandi_benchmark_price_kg) / mandi_benchmark_price_kg

        if pct_deviation > 0.40:
            is_lowball = offered_price_kg < mandi_benchmark_price_kg
            severity = "CRITICAL" if pct_deviation > 0.70 else "HIGH"
            reason_code = "DEAL_OFFER_EXTREME_LOWBALL" if is_lowball else "DEAL_OFFER_EXTREME_PREMIUM"

            return DealAnomalyResult(
                is_anomaly=True,
                reason_code=reason_code,
                severity=severity,
                anomaly_type="offer_price",
                details={
                    "crop_id": crop_id,
                    "offered_price_kg": round(offered_price_kg, 2),
                    "mandi_benchmark_price_kg": round(mandi_benchmark_price_kg, 2),
                    "listing_expected_price_kg": (
                        round(listing_expected_price_kg, 2) if listing_expected_price_kg else None
                    ),
                    "pct_deviation": round(pct_deviation * 100, 1),
                },
            )

        return DealAnomalyResult(
            is_anomaly=False,
            reason_code="CLEAN",
            severity="NONE",
            anomaly_type="clean",
            details={
                "offered_price_kg": round(offered_price_kg, 2),
                "mandi_benchmark_price_kg": round(mandi_benchmark_price_kg, 2),
                "pct_deviation": round(pct_deviation * 100, 1),
            },
        )

    def evaluate_user_cancellations(
        self,
        user_id: int,
        total_interactions: int,
        cancelled_count: int,
        window_days: int = 7,
    ) -> DealAnomalyResult:
        """
        Flags users with serial cancellation behavior (>=3 cancellations & >=50% rate).
        """
        if total_interactions <= 0:
            return DealAnomalyResult(
                is_anomaly=False,
                reason_code="CLEAN",
                severity="NONE",
                anomaly_type="clean",
                details={"user_id": user_id},
            )

        cancel_rate = cancelled_count / total_interactions

        if cancelled_count >= 3 and (cancel_rate >= 0.50 or cancelled_count >= 5):
            severity = "CRITICAL" if cancelled_count >= 5 else "HIGH"
            return DealAnomalyResult(
                is_anomaly=True,
                reason_code="DEAL_SERIAL_CANCELLATIONS",
                severity=severity,
                anomaly_type="cancellations",
                details={
                    "user_id": user_id,
                    "total_interactions": total_interactions,
                    "cancelled_count": cancelled_count,
                    "cancel_rate_pct": round(cancel_rate * 100, 1),
                    "window_days": window_days,
                },
            )

        return DealAnomalyResult(
            is_anomaly=False,
            reason_code="CLEAN",
            severity="NONE",
            anomaly_type="clean",
            details={
                "user_id": user_id,
                "cancel_rate_pct": round(cancel_rate * 100, 1),
            },
        )

    def evaluate_listing_photos(
        self,
        current_farmer_id: int,
        photo_hashes: list[str],
        as_of: date | None = None,
    ) -> DealAnomalyResult:
        """
        Detects stolen or recycled photo hashes in produce listings.
        """
        as_of = as_of or date.today()

        for ph in photo_hashes:
            if ph in self._photo_hash_registry:
                prior = self._photo_hash_registry[ph]
                prior_farmer = prior["farmer_id"]
                prior_listing = prior["listing_id"]
                prior_date = prior["created_at"]

                # Case A: Different farmer -> image theft / fake listing
                if prior_farmer != current_farmer_id:
                    return DealAnomalyResult(
                        is_anomaly=True,
                        reason_code="DEAL_STOLEN_PHOTO_REUSE",
                        severity="CRITICAL",
                        anomaly_type="photo_reuse",
                        details={
                            "matched_hash": ph,
                            "prior_farmer_id": prior_farmer,
                            "prior_listing_id": prior_listing,
                            "prior_date": prior_date.isoformat() if isinstance(prior_date, date) else str(prior_date),
                        },
                    )

                # Case B: Same farmer, but photo is > 7 days old -> recycled gallery stock
                days_diff = (as_of - prior_date).days if isinstance(prior_date, date) else 10
                if days_diff > 7:
                    return DealAnomalyResult(
                        is_anomaly=True,
                        reason_code="DEAL_STALE_STOCK_PHOTO_REUSE",
                        severity="HIGH",
                        anomaly_type="photo_reuse",
                        details={
                            "matched_hash": ph,
                            "prior_listing_id": prior_listing,
                            "age_days": days_diff,
                        },
                    )

        return DealAnomalyResult(
            is_anomaly=False,
            reason_code="CLEAN",
            severity="NONE",
            anomaly_type="clean",
            details={"hashes_checked": len(photo_hashes)},
        )


deal_anomaly_detector = DealAnomalyDetector()
