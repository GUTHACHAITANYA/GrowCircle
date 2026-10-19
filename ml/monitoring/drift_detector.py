"""
GrowCircle Drift Detector & Post-Launch Model Health Monitoring (ML-7).

Monitors:
1. Feature data drift (Kolmogorov-Smirnov test and Population Stability Index - PSI)
2. Prediction drift between baseline and production serving windows
3. Daily forecast error tracking as actuals arrive (MAE, sMAPE, Pinball loss)
4. Empirical quantile interval calibration (P10-P90 coverage vs nominal 80%)
5. Computer vision confidence distribution, blur, and glare shifts
6. Voice and chat agent failure rates and WER degradation by language
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


class DriftDetector:
    """
    Engine for data drift, prediction drift, forecast calibration,
    vision confidence shifts, and voice agent language failure tracking.
    """

    @staticmethod
    def compute_ks_drift(
        reference: list[float] | np.ndarray | pd.Series,
        current: list[float] | np.ndarray | pd.Series,
        alpha: float = 0.05,
    ) -> dict[str, Any]:
        """
        Performs two-sample Kolmogorov-Smirnov test between reference and current distributions.
        Returns KS statistic, p-value, and drift flag.
        """
        ref_arr = np.asarray(reference, dtype=float)
        curr_arr = np.asarray(current, dtype=float)

        ref_clean = ref_arr[~np.isnan(ref_arr)]
        curr_clean = curr_arr[~np.isnan(curr_arr)]

        if len(ref_clean) < 5 or len(curr_clean) < 5:
            return {
                "statistic": 0.0,
                "p_value": 1.0,
                "drift_detected": False,
                "sample_size_ref": len(ref_clean),
                "sample_size_curr": len(curr_clean),
                "note": "Insufficient samples for statistical significance (<5)",
            }

        res = stats.ks_2samp(ref_clean, curr_clean)
        stat = float(res.statistic)
        p_val = float(res.pvalue)
        drift_detected = p_val < alpha

        return {
            "statistic": round(stat, 4),
            "p_value": round(p_val, 6),
            "alpha": alpha,
            "drift_detected": drift_detected,
            "sample_size_ref": len(ref_clean),
            "sample_size_curr": len(curr_clean),
        }

    @staticmethod
    def compute_psi(
        reference: list[float] | np.ndarray | pd.Series,
        current: list[float] | np.ndarray | pd.Series,
        num_bins: int = 10,
    ) -> float:
        """
        Computes Population Stability Index (PSI).
        Rules of thumb:
        - PSI < 0.10: No significant shift (Stable)
        - 0.10 <= PSI < 0.25: Moderate shift (Monitor closely)
        - PSI >= 0.25: Significant shift (Retraining / investigation required)
        """
        ref_arr = np.asarray(reference, dtype=float)
        curr_arr = np.asarray(current, dtype=float)

        ref_clean = ref_arr[~np.isnan(ref_arr)]
        curr_clean = curr_arr[~np.isnan(curr_arr)]

        if len(ref_clean) < 10 or len(curr_clean) < 10:
            return 0.0

        # Create quantiles on reference
        quantiles = np.linspace(0, 100, num_bins + 1)
        bin_edges = np.percentile(ref_clean, quantiles)
        bin_edges[0] -= 1e-5
        bin_edges[-1] += 1e-5

        # Handle duplicate bin edges if variance is low
        bin_edges = np.unique(bin_edges)
        if len(bin_edges) < 2:
            return 0.0

        # Enforce infinite boundary edges so extreme drift values are captured
        bin_edges[0] = -np.inf
        bin_edges[-1] = np.inf

        ref_counts, _ = np.histogram(ref_clean, bins=bin_edges)
        curr_counts, _ = np.histogram(curr_clean, bins=bin_edges)

        eps = 1e-4
        ref_pct = (ref_counts / len(ref_clean)) + eps
        curr_pct = (curr_counts / len(curr_clean)) + eps

        # Normalize back so sum equals 1
        ref_pct /= np.sum(ref_pct)
        curr_pct /= np.sum(curr_pct)

        psi_val = np.sum((curr_pct - ref_pct) * np.log(curr_pct / ref_pct))
        return float(round(psi_val, 4))

    @classmethod
    def detect_feature_data_drift(
        cls,
        ref_df: pd.DataFrame,
        curr_df: pd.DataFrame,
        feature_cols: list[str] | None = None,
        alpha: float = 0.05,
    ) -> dict[str, Any]:
        """
        Evaluates drift across all numerical features using KS tests and PSI.
        Flags dataset-level drift if more than 33% of features exhibit drift.
        """
        if feature_cols is None:
            num_cols = ref_df.select_dtypes(include=[np.number]).columns.tolist()
            feature_cols = [c for c in num_cols if c in curr_df.columns]

        feature_reports: dict[str, Any] = {}
        drifted_count = 0

        for col in feature_cols:
            ks_res = cls.compute_ks_drift(ref_df[col], curr_df[col], alpha=alpha)
            psi_val = cls.compute_psi(ref_df[col], curr_df[col])

            is_drifted = ks_res["drift_detected"] or (psi_val >= 0.25)
            if is_drifted:
                drifted_count += 1

            feature_reports[col] = {
                "ks_statistic": ks_res["statistic"],
                "p_value": ks_res["p_value"],
                "psi": psi_val,
                "drift_detected": is_drifted,
                "psi_category": (
                    "STABLE"
                    if psi_val < 0.10
                    else "MODERATE"
                    if psi_val < 0.25
                    else "SIGNIFICANT"
                ),
            }

        total_features = max(1, len(feature_cols))
        drift_share = round(drifted_count / total_features, 3)
        dataset_drift_detected = drift_share >= 0.33

        return {
            "dataset_drift_detected": dataset_drift_detected,
            "drift_share": drift_share,
            "drifted_features_count": drifted_count,
            "total_features_count": len(feature_cols),
            "feature_reports": feature_reports,
        }

    @classmethod
    def detect_prediction_drift(
        cls,
        ref_predictions: list[float] | np.ndarray,
        curr_predictions: list[float] | np.ndarray,
    ) -> dict[str, Any]:
        """
        Checks for distribution drift in forecast or pricing model outputs.
        """
        ks_res = cls.compute_ks_drift(ref_predictions, curr_predictions)
        psi_val = cls.compute_psi(ref_predictions, curr_predictions)

        prediction_drift = ks_res["drift_detected"] or (psi_val >= 0.20)
        return {
            "prediction_drift_detected": prediction_drift,
            "ks_statistic": ks_res["statistic"],
            "p_value": ks_res["p_value"],
            "psi": psi_val,
            "psi_category": (
                "STABLE"
                if psi_val < 0.10
                else "MODERATE"
                if psi_val < 0.25
                else "SIGNIFICANT"
            ),
        }

    @classmethod
    def track_daily_forecast_errors(
        cls,
        records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Evaluates forecast performance against realized mandi actuals:
        - MAE on P50
        - sMAPE percentage
        - Pinball losses for P10 and P90 quantiles
        - Empirical interval coverage (target: ~80% for P10-P90 interval)
        - Calibration status (flagged if coverage <65% or >95%)
        """
        if not records:
            return {
                "total_evaluations": 0,
                "mae": 0.0,
                "smape_pct": 0.0,
                "interval_coverage_pct": 0.0,
                "is_well_calibrated": True,
                "calibration_status": "NO_DATA",
                "per_crop_breakdown": {},
            }

        errors = []
        smapes = []
        p10_pinball = []
        p90_pinball = []
        inside_interval_count = 0

        crop_stats: dict[str, list[tuple[float, float, float, float]]] = {}

        for r in records:
            actual = float(r["actual_price"])
            p10 = float(r["predicted_p10"])
            p50 = float(r["predicted_p50"])
            p90 = float(r["predicted_p90"])
            crop = str(r.get("crop", "general")).lower()

            # Absolute Error
            err = abs(actual - p50)
            errors.append(err)

            # sMAPE
            denom = abs(actual) + abs(p50)
            smape = 200.0 * err / denom if denom > 0 else 0.0
            smapes.append(smape)

            # Pinball loss P10 (q = 0.10)
            diff_10 = actual - p10
            loss_10 = 0.10 * diff_10 if diff_10 >= 0 else (0.10 - 1.0) * diff_10
            p10_pinball.append(loss_10)

            # Pinball loss P90 (q = 0.90)
            diff_90 = actual - p90
            loss_90 = 0.90 * diff_90 if diff_90 >= 0 else (0.90 - 1.0) * diff_90
            p90_pinball.append(loss_90)

            # Empirical Coverage
            if p10 <= actual <= p90:
                inside_interval_count += 1

            if crop not in crop_stats:
                crop_stats[crop] = []
            crop_stats[crop].append((actual, p10, p50, p90))

        n = len(records)
        mae = float(np.mean(errors))
        mean_smape = float(np.mean(smapes))
        coverage_pct = round((inside_interval_count / n) * 100.0, 1)

        # Well-calibrated condition: 80% nominal interval should observe 65% - 95%
        is_well_calibrated = 65.0 <= coverage_pct <= 95.0
        calibration_status = (
            "CALIBRATED"
            if is_well_calibrated
            else "UNDER_COVERAGE"
            if coverage_pct < 65.0
            else "OVER_COVERAGE"
        )

        per_crop_breakdown: dict[str, Any] = {}
        for crop_name, tuples in crop_stats.items():
            c_n = len(tuples)
            c_mae = float(np.mean([abs(t[0] - t[2]) for t in tuples]))
            c_cov = round(sum(1 for t in tuples if t[1] <= t[0] <= t[3]) / c_n * 100.0, 1)
            per_crop_breakdown[crop_name] = {
                "evaluations": c_n,
                "mae": round(c_mae, 2),
                "interval_coverage_pct": c_cov,
            }

        return {
            "total_evaluations": n,
            "mae": round(mae, 2),
            "smape_pct": round(mean_smape, 2),
            "pinball_loss_p10": round(float(np.mean(p10_pinball)), 3),
            "pinball_loss_p90": round(float(np.mean(p90_pinball)), 3),
            "nominal_coverage_pct": 80.0,
            "interval_coverage_pct": coverage_pct,
            "is_well_calibrated": is_well_calibrated,
            "calibration_status": calibration_status,
            "per_crop_breakdown": per_crop_breakdown,
        }

    @classmethod
    def track_vision_confidence_distribution(
        cls,
        vision_records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Tracks computer vision model inference confidence, blur shifts, and glare defects.
        """
        if not vision_records:
            return {
                "total_inferences": 0,
                "mean_confidence": 0.0,
                "low_confidence_rate_pct": 0.0,
                "blur_rate_pct": 0.0,
                "glare_rate_pct": 0.0,
                "status": "NO_DATA",
            }

        confs = [float(r["confidence"]) for r in vision_records]
        low_conf_count = sum(1 for c in confs if c < 0.65)
        blur_count = sum(1 for r in vision_records if r.get("blur_score", 150.0) < 100.0 or r.get("is_blurry", False))
        glare_count = sum(1 for r in vision_records if r.get("glare_detected", False))

        n = len(vision_records)
        low_conf_pct = round((low_conf_count / n) * 100.0, 1)
        blur_pct = round((blur_count / n) * 100.0, 1)
        glare_pct = round((glare_count / n) * 100.0, 1)

        is_healthy = low_conf_pct <= 20.0 and (blur_pct + glare_pct) <= 30.0

        return {
            "total_inferences": n,
            "mean_confidence": round(float(np.mean(confs)), 3),
            "median_confidence": round(float(np.median(confs)), 3),
            "low_confidence_threshold": 0.65,
            "low_confidence_rate_pct": low_conf_pct,
            "blur_rate_pct": blur_pct,
            "glare_rate_pct": glare_pct,
            "status": "HEALTHY" if is_healthy else "DRIFT_ALERT",
        }

    @classmethod
    def track_voice_agent_failure_rates(
        cls,
        logs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Tracks failure rates, WER, intent errors, hallucination attempts,
        and KVK escalation rates broken down by language (te, hi, gu, en).
        """
        by_lang: dict[str, list[dict[str, Any]]] = {"te": [], "hi": [], "gu": [], "en": []}
        for log in logs:
            lang = log.get("language", "en")
            if lang in by_lang:
                by_lang[lang].append(log)
            else:
                by_lang["en"].append(log)

        lang_summaries: dict[str, Any] = {}
        overall_calls = len(logs)
        overall_failures = 0

        for lang, lang_logs in by_lang.items():
            count = len(lang_logs)
            if count == 0:
                lang_summaries[lang] = {
                    "total_calls": 0,
                    "wer_avg": 0.0,
                    "intent_error_rate_pct": 0.0,
                    "hallucination_attempt_rate_pct": 0.0,
                    "kvk_fallback_rate_pct": 0.0,
                    "status": "INACTIVE",
                }
                continue

            intent_errs = sum(1 for entry in lang_logs if not entry.get("intent_matched", True))
            hallucinations = sum(1 for entry in lang_logs if entry.get("hallucination_detected", False))
            kvk_fallbacks = sum(1 for entry in lang_logs if entry.get("routed_to_kvk", False))
            wers = [float(entry.get("wer", 0.04)) for entry in lang_logs]

            overall_failures += intent_errs + hallucinations

            intent_err_pct = round((intent_errs / count) * 100.0, 1)
            hallucination_pct = round((hallucinations / count) * 100.0, 2)
            kvk_fallback_pct = round((kvk_fallbacks / count) * 100.0, 1)

            # Healthy if intent error < 20% and zero ungrounded hallucinations
            status_lang = (
                "HEALTHY"
                if intent_err_pct <= 20.0 and hallucination_pct == 0.0
                else "DEGRADED"
                if intent_err_pct <= 35.0 and hallucination_pct == 0.0
                else "FAILING"
            )

            lang_summaries[lang] = {
                "total_calls": count,
                "wer_avg": round(float(np.mean(wers)), 3),
                "intent_error_rate_pct": intent_err_pct,
                "hallucination_attempt_rate_pct": hallucination_pct,
                "kvk_fallback_rate_pct": kvk_fallback_pct,
                "status": status_lang,
            }

        return {
            "total_logged_interactions": overall_calls,
            "overall_failure_rate_pct": (
                round((overall_failures / max(1, overall_calls)) * 100.0, 1)
            ),
            "by_language": lang_summaries,
        }
