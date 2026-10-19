"""
Multi-Layer Agricultural Price Anomaly Detector (Phase ML-2).
Combines:
1. Deterministic Rule Layer: Unit errors, 10x spikes/crashes, inverted bounds, non-positive values.
2. Statistical Layer: Robust Z-score on forecast residuals & Isolation Forest per crop.
3. Auto-Clearing Rules: Corroboration via spatial neighbor mandis or extreme arrival shocks.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)

# Biological plausibility limits (₹ / kg) for AP crops
CROP_LIMITS_KG: dict[str, dict[str, float]] = {
    "banana": {"min_kg": 1.0, "max_kg": 180.0, "unit_error_thresh": 450.0},
    "tomato": {"min_kg": 0.5, "max_kg": 250.0, "unit_error_thresh": 500.0},
    "onion": {"min_kg": 1.0, "max_kg": 180.0, "unit_error_thresh": 400.0},
    "potato": {"min_kg": 1.0, "max_kg": 120.0, "unit_error_thresh": 350.0},
}

MODELS_DIR = Path("ml/models/artifacts/anomaly")


@dataclass
class PriceAnomalyResult:
    is_anomaly: bool
    reason_code: str
    severity: str  # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'NONE'
    layer: str  # 'rule', 'statistical', 'clean'
    is_auto_cleared: bool = False
    auto_cleared_reason: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_anomaly": self.is_anomaly,
            "reason_code": self.reason_code,
            "severity": self.severity,
            "layer": self.layer,
            "is_auto_cleared": self.is_auto_cleared,
            "auto_cleared_reason": self.auto_cleared_reason,
            "metrics": self.metrics,
        }


class PriceAnomalyDetector:
    """
    Two-layer Price Anomaly Detector with auto-clearing logic.
    """

    def __init__(self, data_path: str = "data/processed/cleaned_mandi_prices.csv") -> None:
        self.data_path = Path(data_path)
        self.history_df = self._load_data()
        self.iso_forests: dict[str, IsolationForest] = {}
        self._init_isolation_forests()

    def _load_data(self) -> pd.DataFrame:
        if self.data_path.exists():
            df = pd.read_csv(self.data_path)
            df["price_date"] = pd.to_datetime(df["price_date"]).dt.date
            return df
        return pd.DataFrame()

    def _init_isolation_forests(self) -> None:
        """Trains or loads an Isolation Forest model per crop."""
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        if self.history_df.empty:
            return

        clean = self.history_df[~self.history_df.get("is_outlier", False)].copy()

        for crop in clean["crop_id"].unique():
            model_file = MODELS_DIR / f"iforest_{crop}.joblib"
            crop_df = clean[clean["crop_id"] == crop].sort_values("price_date")
            if len(crop_df) < 50:
                continue

            if model_file.exists():
                try:
                    self.iso_forests[crop] = joblib.load(model_file)
                    continue
                except Exception:
                    pass

            # Extract features for training
            features = self._extract_crop_features(crop_df)
            if len(features) >= 50:
                clf = IsolationForest(
                    n_estimators=100,
                    contamination=0.03,
                    random_state=42,
                )
                clf.fit(features)
                self.iso_forests[crop] = clf
                joblib.dump(clf, model_file)

    def _extract_crop_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extracts 5 multi-variate features for Isolation Forest."""
        feats = pd.DataFrame(index=df.index)
        feats["log_price"] = np.log(df["modal_price_kg"].clip(lower=0.1))

        # Rolling 7d mean
        ma7 = df["modal_price_kg"].rolling(7, min_periods=1).mean()
        feats["ratio_to_ma7"] = (df["modal_price_kg"] / ma7.clip(lower=0.1)).fillna(1.0)

        # 1d return
        lag1 = df["modal_price_kg"].shift(1).bfill()
        feats["pct_return_1d"] = ((df["modal_price_kg"] - lag1) / lag1.clip(lower=0.1)).fillna(0.0)

        # Spread ratio
        modal_c = df["modal_price_kg"].clip(lower=0.1)
        feats["spread_ratio"] = ((df["max_price_kg"] - df["min_price_kg"]) / modal_c).fillna(0.0)

        # Arrival volume
        arrivals = df.get("arrival_tonnes", pd.Series(0.0, index=df.index)).fillna(0.0)
        feats["log_arrivals"] = np.log1p(arrivals.clip(lower=0.0))

        return feats.fillna(0.0)

    def evaluate_price(
        self,
        record: dict[str, Any],
        as_of: date | None = None,
    ) -> PriceAnomalyResult:
        """
        Evaluates a single price record against the Rule Layer, Statistical Layer,
        and Auto-Clearing heuristics.
        """
        crop_id = str(record.get("crop_id", "")).lower().strip()
        mandi_id = str(record.get("mandi_id", "")).strip()

        try:
            modal = float(record.get("modal_price_kg", 0.0))
            min_p = float(record.get("min_price_kg", modal))
            max_p = float(record.get("max_price_kg", modal))
            arrivals = float(record.get("arrival_tonnes", 0.0))
        except (ValueError, TypeError):
            return PriceAnomalyResult(
                is_anomaly=True,
                reason_code="RULE_INVALID_DATA_TYPE",
                severity="CRITICAL",
                layer="rule",
                metrics={"record": record},
            )

        if as_of is None:
            as_of = record.get("price_date", date.today())
            if isinstance(as_of, str):
                as_of = pd.to_datetime(as_of).date()

        # -------------------------------------------------------------
        # 1. Deterministic Rule Layer
        # -------------------------------------------------------------
        # A. Non-positive or zero price
        if modal <= 0.0 or min_p <= 0.0 or max_p <= 0.0:
            return PriceAnomalyResult(
                is_anomaly=True,
                reason_code="RULE_NEGATIVE_OR_ZERO",
                severity="CRITICAL",
                layer="rule",
                metrics={"modal": modal, "min": min_p, "max": max_p},
            )

        # B. Inverted range: min > max
        if min_p > max_p:
            return PriceAnomalyResult(
                is_anomaly=True,
                reason_code="RULE_INVERTED_RANGE",
                severity="CRITICAL",
                layer="rule",
                metrics={"min": min_p, "max": max_p},
            )

        # C. Modal out of range [min, max]
        if modal < min_p or modal > max_p:
            return PriceAnomalyResult(
                is_anomaly=True,
                reason_code="RULE_MODAL_OUT_OF_BOUNDS",
                severity="HIGH",
                layer="rule",
                metrics={"modal": modal, "min": min_p, "max": max_p},
            )

        # D. Unit error (Agmarknet quintal entered in kg field, or vice versa)
        crop_bounds = CROP_LIMITS_KG.get(
            crop_id, {"min_kg": 0.5, "max_kg": 200.0, "unit_error_thresh": 400.0}
        )
        if modal >= crop_bounds["unit_error_thresh"]:
            return PriceAnomalyResult(
                is_anomaly=True,
                reason_code="RULE_UNIT_ERROR",
                severity="CRITICAL",
                layer="rule",
                metrics={"modal": modal, "unit_thresh": crop_bounds["unit_error_thresh"]},
            )

        # Extreme biological lower ceiling
        if modal < crop_bounds["min_kg"]:
            return PriceAnomalyResult(
                is_anomaly=True,
                reason_code="RULE_BELOW_BIOLOGICAL_FLOOR",
                severity="CRITICAL",
                layer="rule",
                metrics={"modal": modal, "floor": crop_bounds["min_kg"]},
            )

        # Retrieve recent history for reference price
        ref_df = self._get_recent_history(mandi_id, crop_id, as_of)
        if not ref_df.empty:
            recent_modal_avg = float(ref_df.tail(7)["modal_price_kg"].mean())
            last_modal = float(ref_df.iloc[-1]["modal_price_kg"])

            # E. 10x vertical jump or crash
            if recent_modal_avg > 0:
                if modal >= recent_modal_avg * 10.0:
                    return PriceAnomalyResult(
                        is_anomaly=True,
                        reason_code="RULE_10X_SPIKE",
                        severity="CRITICAL",
                        layer="rule",
                        metrics={"modal": modal, "recent_avg": round(recent_modal_avg, 2)},
                    )
                if modal <= recent_modal_avg / 10.0:
                    return PriceAnomalyResult(
                        is_anomaly=True,
                        reason_code="RULE_10X_CRASH",
                        severity="CRITICAL",
                        layer="rule",
                        metrics={"modal": modal, "recent_avg": round(recent_modal_avg, 2)},
                    )
        else:
            recent_modal_avg = modal
            last_modal = modal

        # -------------------------------------------------------------
        # 2. Statistical Layer
        # -------------------------------------------------------------
        # A. Robust Z-Score on Residual relative to moving average / forecast
        # Residual e = |modal - expected|
        residual = abs(modal - recent_modal_avg)
        hist_residuals = []
        if not ref_df.empty and len(ref_df) >= 7:
            diffs = ref_df["modal_price_kg"].diff().abs().dropna()
            hist_residuals = diffs.tolist()

        mad = float(np.median(hist_residuals)) if hist_residuals else 2.0
        mad = max(mad, 0.5)  # Avoid zero division
        # Consistent scale estimator: 1.4826 * MAD
        robust_z = residual / (1.4826 * mad)

        stat_flagged = False
        stat_reason = "NONE"
        stat_severity = "LOW"

        if robust_z >= 3.5:
            stat_flagged = True
            stat_reason = "STAT_RESIDUAL_ZSCORE"
            stat_severity = "HIGH" if robust_z >= 5.0 else "MEDIUM"

        # B. Isolation Forest Multivariate Anomaly
        if crop_id in self.iso_forests and not stat_flagged:
            ratio_ma7 = modal / max(recent_modal_avg, 0.1)
            pct_return = (modal - last_modal) / max(last_modal, 0.1)
            spread_ratio = (max_p - min_p) / max(modal, 0.1)
            sample_feats = pd.DataFrame(
                [
                    {
                        "log_price": math.log(max(modal, 0.1)),
                        "ratio_to_ma7": ratio_ma7,
                        "pct_return_1d": pct_return,
                        "spread_ratio": spread_ratio,
                        "log_arrivals": math.log1p(max(arrivals, 0.0)),
                    }
                ]
            )
            score = float(self.iso_forests[crop_id].decision_function(sample_feats)[0])
            if score < -0.10:
                stat_flagged = True
                stat_reason = "STAT_ISOLATION_FOREST"
                stat_severity = "MEDIUM"

        if not stat_flagged:
            return PriceAnomalyResult(
                is_anomaly=False,
                reason_code="CLEAN",
                severity="NONE",
                layer="clean",
                metrics={"robust_z": round(robust_z, 2), "modal": modal},
            )

        # -------------------------------------------------------------
        # 3. Auto-Clearing Rules for Statistical Anomalies
        # -------------------------------------------------------------
        # Corroboration 1: Spatial neighbors experiencing similar swing
        price_delta_pct = (modal - last_modal) / max(last_modal, 0.1)
        is_corroborated_spatial = self._check_spatial_corroboration(
            mandi_id, crop_id, as_of, price_delta_pct
        )
        if is_corroborated_spatial:
            return PriceAnomalyResult(
                is_anomaly=True,
                reason_code=stat_reason,
                severity=stat_severity,
                layer="statistical",
                is_auto_cleared=True,
                auto_cleared_reason="Spatial corroboration: Regional price shift confirmed by neighbor mandis within 150km",
                metrics={"robust_z": round(robust_z, 2), "modal": modal, "spatial_corroborated": True},
            )

        # Corroboration 2: Arrival volume surge explaining price drop (or collapse explaining surge)
        recent_arrivals_avg = (
            float(ref_df.tail(7)["arrival_tonnes"].mean()) if not ref_df.empty else 0.0
        )
        if recent_arrivals_avg > 0 and arrivals > 0:
            if modal < last_modal and arrivals >= recent_arrivals_avg * 3.0:
                return PriceAnomalyResult(
                    is_anomaly=True,
                    reason_code=stat_reason,
                    severity=stat_severity,
                    layer="statistical",
                    is_auto_cleared=True,
                    auto_cleared_reason="Supply shock: Heavy market arrival volume explains sharp price drop",
                    metrics={"robust_z": round(robust_z, 2), "arrivals_surge": round(arrivals / recent_arrivals_avg, 1)},
                )

        # If not auto-cleared, must go to Admin Review Queue
        return PriceAnomalyResult(
            is_anomaly=True,
            reason_code=stat_reason,
            severity=stat_severity,
            layer="statistical",
            is_auto_cleared=False,
            metrics={"robust_z": round(robust_z, 2), "modal": modal},
        )

    def _get_recent_history(self, mandi_id: str, crop_id: str, as_of: date) -> pd.DataFrame:
        if self.history_df.empty:
            return pd.DataFrame()
        return self.history_df[
            (self.history_df["mandi_id"] == mandi_id)
            & (self.history_df["crop_id"] == crop_id)
            & (self.history_df["price_date"] < as_of)
        ].sort_values("price_date")

    def _check_spatial_corroboration(
        self,
        mandi_id: str,
        crop_id: str,
        as_of: date,
        direction_delta: float,
    ) -> bool:
        """
        Checks if nearby mandis recorded price movements in the same direction
        (e.g. both shifted > 12%).
        """
        if self.history_df.empty or abs(direction_delta) < 0.12:
            return False

        same_date = self.history_df[
            (self.history_df["crop_id"] == crop_id)
            & (self.history_df["price_date"] == as_of)
            & (self.history_df["mandi_id"] != mandi_id)
        ]

        if same_date.empty:
            return False

        # Look for neighboring mandis showing same direction movement
        for _, neighbor in same_date.iterrows():
            n_mandi = neighbor["mandi_id"]
            n_hist = self._get_recent_history(n_mandi, crop_id, as_of)
            if not n_hist.empty:
                n_last = float(n_hist.iloc[-1]["modal_price_kg"])
                n_curr = float(neighbor["modal_price_kg"])
                n_delta = (n_curr - n_last) / max(n_last, 0.1)

                # Same direction and significant
                if (direction_delta > 0 and n_delta > 0.10) or (direction_delta < 0 and n_delta < -0.10):
                    return True
        return False


price_anomaly_detector = PriceAnomalyDetector()
