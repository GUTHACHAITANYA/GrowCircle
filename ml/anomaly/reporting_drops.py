"""
Reporting Drop and Source Outage Detector (Phase ML-2).
Learns the historical distribution of reporting mandis per day-of-week,
and raises alerts on anomalous drops indicating possible upstream data.gov.in / APMC portal outages.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ReportingDropResult:
    target_date: str
    day_of_week: str
    actual_reporting_mandis: int
    expected_reporting_mandis: float
    std_reporting_mandis: float
    drop_ratio: float
    drop_zscore: float
    status: str  # 'HEALTHY', 'WARNING_DROP', 'CRITICAL_OUTAGE', 'NORMAL_WEEKEND'
    is_outage_alert: bool
    alert_message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_date": self.target_date,
            "day_of_week": self.day_of_week,
            "actual_reporting_mandis": self.actual_reporting_mandis,
            "expected_reporting_mandis": round(self.expected_reporting_mandis, 1),
            "std_reporting_mandis": round(self.std_reporting_mandis, 2),
            "drop_ratio": round(self.drop_ratio, 3),
            "drop_zscore": round(self.drop_zscore, 2),
            "status": self.status,
            "is_outage_alert": self.is_outage_alert,
            "alert_message": self.alert_message,
        }


WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


class ReportingDropDetector:
    """
    Learns normal weekday reporting patterns and detects upstream data outages.
    """

    def __init__(self, data_path: str = "data/processed/cleaned_mandi_prices.csv") -> None:
        self.data_path = Path(data_path)
        self.baseline_stats: dict[int, dict[str, float]] = {}
        self._learn_baselines()

    def _learn_baselines(self) -> None:
        """Computes mean and std of reporting mandis per weekday."""
        if not self.data_path.exists():
            # Default reasonable priors for AP if no data file
            for d in range(7):
                if d < 6:  # Mon - Sat
                    self.baseline_stats[d] = {"mean": 18.0, "std": 2.5}
                else:  # Sun
                    self.baseline_stats[d] = {"mean": 2.0, "std": 1.2}
            return

        df = pd.read_csv(self.data_path)
        df["price_date"] = pd.to_datetime(df["price_date"])
        df["weekday"] = df["price_date"].dt.weekday

        # Group by date and count distinct mandis
        daily_counts = (
            df.groupby(["price_date", "weekday"])["mandi_id"]
            .nunique()
            .reset_index(name="mandi_count")
        )

        for d in range(7):
            w_counts = daily_counts[daily_counts["weekday"] == d]["mandi_count"]
            if len(w_counts) >= 5:
                mean_val = float(w_counts.mean())
                std_val = float(w_counts.std()) if len(w_counts) > 1 else 1.5
                std_val = max(std_val, 1.0)
                self.baseline_stats[d] = {
                    "mean": max(mean_val, 1.0),
                    "std": std_val,
                }
            else:
                self.baseline_stats[d] = {
                    "mean": 18.0 if d < 6 else 2.0,
                    "std": 2.0,
                }

    def evaluate_reporting(
        self,
        target_date: date,
        actual_mandis_count: int,
    ) -> ReportingDropResult:
        """
        Evaluates whether the count of reporting mandis on target_date
        constitutes an anomalous drop indicating an upstream outage.
        """
        w = target_date.weekday()
        day_name = WEEKDAY_NAMES[w]
        stats = self.baseline_stats.get(w, {"mean": 18.0, "std": 2.0})
        mu = stats["mean"]
        sigma = stats["std"]

        drop_ratio = actual_mandis_count / max(mu, 1.0)
        # Positive Z indicates a drop below mean
        drop_zscore = (mu - actual_mandis_count) / max(sigma, 1.0)

        # 1. Sunday / low-volume weekend baseline check
        if mu <= 3.0:
            return ReportingDropResult(
                target_date=target_date.isoformat(),
                day_of_week=day_name,
                actual_reporting_mandis=actual_mandis_count,
                expected_reporting_mandis=mu,
                std_reporting_mandis=sigma,
                drop_ratio=drop_ratio,
                drop_zscore=drop_zscore,
                status="NORMAL_WEEKEND",
                is_outage_alert=False,
                alert_message=f"Normal low weekend volume on {day_name} ({actual_mandis_count} reporting).",
            )

        # 2. Critical source outage: < 35% of expected or Z >= 3.0
        if drop_ratio <= 0.35 or drop_zscore >= 3.0:
            return ReportingDropResult(
                target_date=target_date.isoformat(),
                day_of_week=day_name,
                actual_reporting_mandis=actual_mandis_count,
                expected_reporting_mandis=mu,
                std_reporting_mandis=sigma,
                drop_ratio=drop_ratio,
                drop_zscore=drop_zscore,
                status="CRITICAL_OUTAGE",
                is_outage_alert=True,
                alert_message=(
                    f"CRITICAL SOURCE OUTAGE ALERT: Severe drop in reporting mandis "
                    f"({actual_mandis_count} active vs expected {mu:.1f}, Z={drop_zscore:.1f}). "
                    f"Upstream portal (data.gov.in / Agmarknet) may be down or experiencing ingestion failure."
                ),
            )

        # 3. Warning drop: 35% - 60% of expected or Z >= 2.0
        if drop_ratio <= 0.60 or drop_zscore >= 2.0:
            return ReportingDropResult(
                target_date=target_date.isoformat(),
                day_of_week=day_name,
                actual_reporting_mandis=actual_mandis_count,
                expected_reporting_mandis=mu,
                std_reporting_mandis=sigma,
                drop_ratio=drop_ratio,
                drop_zscore=drop_zscore,
                status="WARNING_DROP",
                is_outage_alert=True,
                alert_message=(
                    f"REPORTING WARNING: Unusual drop in reporting mandis "
                    f"({actual_mandis_count} active vs expected {mu:.1f}, Z={drop_zscore:.1f})."
                ),
            )

        # 4. Healthy normal operations
        return ReportingDropResult(
            target_date=target_date.isoformat(),
            day_of_week=day_name,
            actual_reporting_mandis=actual_mandis_count,
            expected_reporting_mandis=mu,
            std_reporting_mandis=sigma,
            drop_ratio=drop_ratio,
            drop_zscore=drop_zscore,
            status="HEALTHY",
            is_outage_alert=False,
            alert_message=f"Reporting volume healthy ({actual_mandis_count} active vs expected {mu:.1f}).",
        )


reporting_drop_detector = ReportingDropDetector()
