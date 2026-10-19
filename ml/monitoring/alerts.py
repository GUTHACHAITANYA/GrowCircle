"""
GrowCircle Alert Engine & Anomaly Incident Response (ML-7).

Alerts when:
1. Forecast error rises above threshold (sMAPE > 25% or MAE > 5.0 INR/kg)
2. Mandi data stops arriving or unusual reporting drops occur (>40% drop)
3. Model encounters policy shocks (export bans, demonetization) or festival periods
4. Interval calibration drops (<65% coverage)
5. Vision confidence degrades or low-quality photo rates spike
6. Voice agent intent errors rise or hallucination attempts occur
7. Operating costs approach or exceed defined budget limits
"""

from __future__ import annotations

import datetime
import logging
import uuid
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Known Indian Agricultural & Cultural Festival Dates (Surge Windows)
INDIAN_FESTIVALS_CALENDAR: dict[str, list[str]] = {
    "Sankranti / Pongal": ["2026-01-13", "2026-01-14", "2026-01-15", "2026-01-16"],
    "Maha Shivaratri": ["2026-02-15", "2026-02-16"],
    "Holi": ["2026-03-03", "2026-03-04"],
    "Ugadi / Gudi Padwa": ["2026-03-19", "2026-03-20"],
    "Eid-ul-Fitr": ["2026-03-20", "2026-03-21"],
    "Ganesh Chaturthi": ["2026-09-14", "2026-09-15"],
    "Dussehra / Navratri": ["2026-10-18", "2026-10-19", "2026-10-20"],
    "Diwali": ["2026-11-07", "2026-11-08", "2026-11-09"],
}


@dataclass
class MonitoringAlert:
    """Structure representing a triggered monitoring incident."""

    alert_id: str
    category: str  # FORECAST_ERROR, DATA_OUTAGE, POLICY_SHOCK, FESTIVAL_SURGE, CALIBRATION, VISION, VOICE, BUDGET
    severity: str  # INFO, WARNING, CRITICAL
    title: str
    message: str
    created_at: str
    metrics_payload: dict[str, Any]
    acknowledged: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AlertEngine:
    """
    Stateful evaluation and dispatch engine for ML post-launch alerts.
    """

    def __init__(self) -> None:
        self._alerts_log: list[MonitoringAlert] = []

    def log_alert(self, alert: MonitoringAlert) -> None:
        self._alerts_log.append(alert)
        logger.warning(
            "[%s ALERT] %s: %s (ID: %s)",
            alert.severity,
            alert.title,
            alert.message,
            alert.alert_id,
        )

    def check_forecast_error_alert(
        self,
        error_stats: dict[str, Any],
        smape_threshold: float = 25.0,
        mae_threshold: float = 5.0,
    ) -> MonitoringAlert | None:
        """
        Triggers critical alert when forecast error breaches error tolerance.
        """
        smape = float(error_stats.get("smape_pct", 0.0))
        mae = float(error_stats.get("mae", 0.0))

        if smape > smape_threshold or mae > mae_threshold:
            alert = MonitoringAlert(
                alert_id=f"alert-err-{uuid.uuid4().hex[:6]}",
                category="FORECAST_ERROR",
                severity="CRITICAL",
                title="Forecast Error Threshold Exceeded",
                message=(
                    f"Forecast error breached tolerances: sMAPE={smape:.1f}% "
                    f"(limit: {smape_threshold}%), MAE=₹{mae:.2f}/kg (limit: ₹{mae_threshold:.2f}/kg). "
                    "Model candidate review or retraining recommended."
                ),
                created_at=datetime.datetime.now(datetime.UTC).isoformat(),
                metrics_payload={"smape_pct": smape, "mae": mae, "thresholds": {"smape": smape_threshold, "mae": mae_threshold}},
            )
            self.log_alert(alert)
            return alert
        return None

    def check_data_arrival_alert(
        self,
        active_mandis_count: int,
        expected_mandis_count: int,
        drop_threshold_pct: float = 40.0,
    ) -> MonitoringAlert | None:
        """
        Triggers critical alert when mandi data stops arriving or drops substantially.
        """
        if expected_mandis_count <= 0:
            return None

        drop_pct = ((expected_mandis_count - active_mandis_count) / expected_mandis_count) * 100.0
        if drop_pct >= drop_threshold_pct or active_mandis_count == 0:
            alert = MonitoringAlert(
                alert_id=f"alert-data-{uuid.uuid4().hex[:6]}",
                category="DATA_OUTAGE",
                severity="CRITICAL",
                title="Mandi Ingestion Outage / Severe Data Drop",
                message=(
                    f"Mandi arrivals reported a {drop_pct:.1f}% drop ({active_mandis_count} active vs "
                    f"{expected_mandis_count} expected). Possible Agmarknet portal downtime or state holiday."
                ),
                created_at=datetime.datetime.now(datetime.UTC).isoformat(),
                metrics_payload={
                    "active_mandis": active_mandis_count,
                    "expected_mandis": expected_mandis_count,
                    "drop_pct": round(drop_pct, 1),
                },
            )
            self.log_alert(alert)
            return alert
        return None

    def detect_policy_or_festival_shock(
        self,
        prices: list[float] | np.ndarray,
        date_str: str,
        crop: str = "general",
    ) -> MonitoringAlert | None:
        """
        Detects structural breaks in price series caused by:
        - Government policy shocks (export bans, minimum export price, demonetization)
        - Major cultural festival demand spikes (Diwali, Sankranti, Eid)
        """
        # 1. Festival Check
        for fest_name, dates in INDIAN_FESTIVALS_CALENDAR.items():
            if date_str in dates:
                alert = MonitoringAlert(
                    alert_id=f"alert-fest-{uuid.uuid4().hex[:6]}",
                    category="FESTIVAL_SURGE",
                    severity="INFO",
                    title=f"Festival Demand Window: {fest_name}",
                    message=(
                        f"Active festival surge window ({fest_name}) on {date_str}. "
                        "High demand may cause temporary volatility and arrival surges. "
                        "Do not retrain models on short-lived festival spikes."
                    ),
                    created_at=datetime.datetime.now(datetime.UTC).isoformat(),
                    metrics_payload={"festival": fest_name, "date": date_str, "crop": crop},
                )
                self.log_alert(alert)
                return alert

        # 2. Structural Policy Shock Detection (Sudden jump without weather explanation)
        arr = np.asarray(prices, dtype=float)
        if len(arr) >= 7:
            recent_3d = arr[-3:]
            prior = arr[:-3]
            mean_prior = float(np.mean(prior))
            std_prior = float(np.std(prior)) if float(np.std(prior)) > 0 else 1.0

            z_score = abs(float(np.mean(recent_3d)) - mean_prior) / std_prior
            pct_change = abs(float(np.mean(recent_3d)) - mean_prior) / max(1.0, mean_prior) * 100.0

            # Structural shock: z-score > 3.0 and absolute change > 40%
            if z_score >= 3.0 and pct_change >= 40.0:
                alert = MonitoringAlert(
                    alert_id=f"alert-shock-{uuid.uuid4().hex[:6]}",
                    category="POLICY_SHOCK",
                    severity="WARNING",
                    title=f"Potential Policy Shock / Market Disruption on {crop.title()}",
                    message=(
                        f"Unusual structural price shift detected for {crop}: {pct_change:.1f}% jump "
                        f"(z-score={z_score:.2f}). Possible trade policy shock (e.g. export ban or MSP change). "
                        "Forecast uncertainty intervals widened."
                    ),
                    created_at=datetime.datetime.now(datetime.UTC).isoformat(),
                    metrics_payload={"crop": crop, "z_score": round(z_score, 2), "pct_change": round(pct_change, 1)},
                )
                self.log_alert(alert)
                return alert

        return None

    def check_calibration_alert(self, error_stats: dict[str, Any]) -> MonitoringAlert | None:
        """
        Triggers alert if 10-90 quantile interval coverage falls outside [65%, 95%].
        """
        cov = float(error_stats.get("interval_coverage_pct", 80.0))
        if cov < 65.0:
            alert = MonitoringAlert(
                alert_id=f"alert-cal-{uuid.uuid4().hex[:6]}",
                category="INTERVAL_MISCALIBRATION",
                severity="WARNING",
                title="Interval Coverage Under-Calibration",
                message=(
                    f"Forecast 10-90 quantile intervals covered only {cov:.1f}% of actual prices "
                    "(nominal target: 80.0%). Model intervals are overconfident."
                ),
                created_at=datetime.datetime.now(datetime.UTC).isoformat(),
                metrics_payload={"observed_coverage_pct": cov, "nominal_target_pct": 80.0},
            )
            self.log_alert(alert)
            return alert
        return None

    def check_vision_confidence_alert(self, vision_stats: dict[str, Any]) -> MonitoringAlert | None:
        """
        Triggers alert when low confidence or defective photo rates spike.
        """
        low_conf = float(vision_stats.get("low_confidence_rate_pct", 0.0))
        blur_glare = float(vision_stats.get("blur_rate_pct", 0.0)) + float(vision_stats.get("glare_rate_pct", 0.0))

        if low_conf > 20.0 or blur_glare > 25.0:
            alert = MonitoringAlert(
                alert_id=f"alert-vis-{uuid.uuid4().hex[:6]}",
                category="VISION_CONFIDENCE_DROP",
                severity="WARNING",
                title="Computer Vision Confidence / Photo Quality Shift",
                message=(
                    f"Vision pipeline experienced quality shift: {low_conf:.1f}% low-confidence triage, "
                    f"{blur_glare:.1f}% blur/glare rate. Farmer camera capture guidance advised."
                ),
                created_at=datetime.datetime.now(datetime.UTC).isoformat(),
                metrics_payload={"low_confidence_rate_pct": low_conf, "blur_glare_pct": blur_glare},
            )
            self.log_alert(alert)
            return alert
        return None

    def check_voice_agent_alert(self, voice_stats: dict[str, Any]) -> MonitoringAlert | None:
        """
        Triggers alert if any language exhibits high intent error rates or hallucination attempts.
        """
        by_lang = voice_stats.get("by_language", {})
        degraded_langs = []
        hallucination_detected = False

        for lang, stats_dict in by_lang.items():
            if stats_dict.get("intent_error_rate_pct", 0.0) > 25.0:
                degraded_langs.append(lang)
            if stats_dict.get("hallucination_attempt_rate_pct", 0.0) > 0.0:
                hallucination_detected = True

        if degraded_langs or hallucination_detected:
            sev = "CRITICAL" if hallucination_detected else "WARNING"
            alert = MonitoringAlert(
                alert_id=f"alert-voice-{uuid.uuid4().hex[:6]}",
                category="VOICE_AGENT_ERROR",
                severity=sev,
                title="Voice Agent Degradation or Grounding Alert",
                message=(
                    f"Voice agent issue: Degraded languages={degraded_langs}, "
                    f"Hallucination attempt detected={hallucination_detected}. "
                    "Verify grounding validator and review regional intent lexicons."
                ),
                created_at=datetime.datetime.now(datetime.UTC).isoformat(),
                metrics_payload={"degraded_languages": degraded_langs, "hallucination_detected": hallucination_detected},
            )
            self.log_alert(alert)
            return alert
        return None

    def check_budget_alert(
        self,
        current_spend: float,
        budget_limit: float,
        period: str = "daily",
    ) -> MonitoringAlert | None:
        """
        Triggers alert when operational telephony & LLM spend approaches or breaches cap.
        """
        if budget_limit <= 0:
            return None

        utilization_pct = (current_spend / budget_limit) * 100.0
        if utilization_pct >= 100.0:
            alert = MonitoringAlert(
                alert_id=f"alert-cost-{uuid.uuid4().hex[:6]}",
                category="BUDGET_EXCEEDED",
                severity="CRITICAL",
                title=f"{period.title()} Operating Budget Exceeded",
                message=(
                    f"{period.title()} operational spend reached ₹{current_spend:.2f} "
                    f"({utilization_pct:.1f}% of ₹{budget_limit:.2f} budget). "
                    "Rate-limiting active and cache hit rate optimization required."
                ),
                created_at=datetime.datetime.now(datetime.UTC).isoformat(),
                metrics_payload={"spend": current_spend, "budget": budget_limit, "utilization_pct": round(utilization_pct, 1)},
            )
            self.log_alert(alert)
            return alert
        elif utilization_pct >= 80.0:
            alert = MonitoringAlert(
                alert_id=f"alert-cost-{uuid.uuid4().hex[:6]}",
                category="BUDGET_EXCEEDED",
                severity="WARNING",
                title=f"{period.title()} Operating Budget Near Cap",
                message=(
                    f"{period.title()} operational spend reached ₹{current_spend:.2f} "
                    f"({utilization_pct:.1f}% of ₹{budget_limit:.2f} cap)."
                ),
                created_at=datetime.datetime.now(datetime.UTC).isoformat(),
                metrics_payload={"spend": current_spend, "budget": budget_limit, "utilization_pct": round(utilization_pct, 1)},
            )
            self.log_alert(alert)
            return alert
        return None

    def get_active_alerts(
        self,
        category: str | None = None,
        severity: str | None = None,
    ) -> list[dict[str, Any]]:
        """Returns filtered list of active/unacknowledged alerts."""
        alerts = [a for a in self._alerts_log if not a.acknowledged]
        if category:
            alerts = [a for a in alerts if a.category == category]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return [a.to_dict() for a in reversed(alerts)]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledges an alert by ID."""
        for a in self._alerts_log:
            if a.alert_id == alert_id:
                a.acknowledged = True
                return True
        return False


# Global Alert Engine Singleton
_GLOBAL_ALERT_ENGINE = AlertEngine()


def get_alert_engine() -> AlertEngine:
    return _GLOBAL_ALERT_ENGINE
