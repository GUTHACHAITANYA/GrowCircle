"""
GrowCircle Cost Controller & Caching Engine (ML-7).

Tracks unit operational expenses for:
- STT Speech Recognition (Bhashini / Sarvam: ₹0.15 / min)
- TTS Speech Synthesis (Neural Indic: ₹0.10 / min)
- LLM Token Inference (₹0.0015/1k input, ₹0.0030/1k output)
- Transactional SMS (DLT compliance: ₹0.12 / SMS)

Enforces aggressive caching with hit-rate telemetry and budget alerts.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

from ml.monitoring.alerts import get_alert_engine

logger = logging.getLogger(__name__)

# Unit Operating Tariffs (in INR ₹)
RATE_STT_PER_SEC: float = 0.15 / 60.0  # ₹0.15 per minute
RATE_TTS_PER_SEC: float = 0.10 / 60.0  # ₹0.10 per minute
RATE_LLM_INPUT_PER_TOKEN: float = 0.0015 / 1000.0
RATE_LLM_OUTPUT_PER_TOKEN: float = 0.0030 / 1000.0
RATE_SMS_PER_MSG: float = 0.12  # ₹0.12 per transactional SMS


class CostController:
    """
    Manages telephony, messaging, and LLM compute budgets and caching efficiency.
    """

    def __init__(
        self,
        daily_budget_inr: float = 5000.0,
        monthly_budget_inr: float = 100000.0,
    ) -> None:
        self.daily_budget_inr = daily_budget_inr
        self.monthly_budget_inr = monthly_budget_inr

        # Cumulative spend accumulators
        self.total_stt_cost_inr: float = 0.0
        self.total_tts_cost_inr: float = 0.0
        self.total_llm_cost_inr: float = 0.0
        self.total_sms_cost_inr: float = 0.0
        self.total_calls_tracked: int = 0
        self.total_call_duration_seconds: float = 0.0
        self.total_messages_tracked: int = 0

        # Caching layer
        self._cache_store: dict[str, tuple[Any, float]] = {}  # key -> (value, expiry_timestamp)
        self.cache_hits: int = 0
        self.cache_misses: int = 0
        self.estimated_savings_inr: float = 0.0

    def record_call_cost(
        self,
        duration_seconds: float = 0.0,
        stt_audio_seconds: float = 0.0,
        tts_audio_seconds: float = 0.0,
        llm_prompt_tokens: int = 0,
        llm_completion_tokens: int = 0,
    ) -> dict[str, Any]:
        """
        Calculates and accumulates operational cost for an IVR/phone call turn.
        """
        self.total_call_duration_seconds += duration_seconds
        c_stt = stt_audio_seconds * RATE_STT_PER_SEC
        c_tts = tts_audio_seconds * RATE_TTS_PER_SEC
        c_llm = (llm_prompt_tokens * RATE_LLM_INPUT_PER_TOKEN) + (llm_completion_tokens * RATE_LLM_OUTPUT_PER_TOKEN)
        turn_cost = c_stt + c_tts + c_llm

        self.total_stt_cost_inr += c_stt
        self.total_tts_cost_inr += c_tts
        self.total_llm_cost_inr += c_llm
        self.total_calls_tracked += 1

        total_spend = self.get_total_spend()
        get_alert_engine().check_budget_alert(total_spend, self.daily_budget_inr, period="daily")

        return {
            "turn_cost_inr": round(turn_cost, 4),
            "stt_cost": round(c_stt, 4),
            "tts_cost": round(c_tts, 4),
            "llm_cost": round(c_llm, 4),
            "cumulative_spend_inr": round(total_spend, 2),
        }

    def record_sms_cost(self, count: int = 1) -> dict[str, Any]:
        """Records outbound OTP or deal confirmation SMS charges."""
        cost = count * RATE_SMS_PER_MSG
        self.total_sms_cost_inr += cost
        self.total_messages_tracked += count

        total_spend = self.get_total_spend()
        get_alert_engine().check_budget_alert(total_spend, self.daily_budget_inr, period="daily")

        return {
            "sms_count": count,
            "cost_inr": round(cost, 4),
            "cumulative_spend_inr": round(total_spend, 2),
        }

    def get_from_cache(self, namespace: str, key: str) -> Any | None:
        """Looks up item in cache. Tracks hit/miss and estimated cost savings."""
        cache_key = f"{namespace}:{key}"
        now = time.time()

        if cache_key in self._cache_store:
            val, expiry = self._cache_store[cache_key]
            if expiry > now:
                self.cache_hits += 1
                # Savings: ~15s TTS synthesis avoided (₹0.025) or 300 token LLM query (₹0.001)
                saved = 0.025 if namespace == "audio_tts" else 0.0015
                self.estimated_savings_inr += saved
                return val
            else:
                del self._cache_store[cache_key]

        self.cache_misses += 1
        return None

    def set_in_cache(self, namespace: str, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Stores item in cache with TTL."""
        cache_key = f"{namespace}:{key}"
        expiry = time.time() + ttl_seconds
        self._cache_store[cache_key] = (value, expiry)

    @staticmethod
    def hash_audio_prompt(text: str, language: str) -> str:
        """Generates deterministic hash for audio synthesis caching."""
        raw = f"{language}:{text.strip().lower()}".encode()
        return hashlib.sha256(raw).hexdigest()[:16]

    def get_total_spend(self) -> float:
        return (
            self.total_stt_cost_inr
            + self.total_tts_cost_inr
            + self.total_llm_cost_inr
            + self.total_sms_cost_inr
        )

    def get_cost_summary(self) -> dict[str, Any]:
        """Returns comprehensive operational cost and caching performance summary."""
        total_spend = self.get_total_spend()
        total_reqs = self.cache_hits + self.cache_misses
        hit_rate = round((self.cache_hits / max(1, total_reqs)) * 100.0, 1)

        daily_util = round((total_spend / max(1.0, self.daily_budget_inr)) * 100.0, 1)
        monthly_util = round((total_spend / max(1.0, self.monthly_budget_inr)) * 100.0, 1)

        budget_status = (
            "WITHIN_BUDGET"
            if daily_util < 80.0
            else "APPROACHING_CAP"
            if daily_util < 100.0
            else "BUDGET_EXCEEDED"
        )

        return {
            "total_spend_inr": round(total_spend, 2),
            "breakdown_inr": {
                "stt_speech": round(self.total_stt_cost_inr, 2),
                "tts_speech": round(self.total_tts_cost_inr, 2),
                "llm_inference": round(self.total_llm_cost_inr, 2),
                "transactional_sms": round(self.total_sms_cost_inr, 2),
            },
            "activity_counts": {
                "total_calls_tracked": self.total_calls_tracked,
                "total_sms_tracked": self.total_messages_tracked,
            },
            "budget": {
                "daily_budget_inr": self.daily_budget_inr,
                "daily_utilization_pct": daily_util,
                "monthly_budget_inr": self.monthly_budget_inr,
                "monthly_utilization_pct": monthly_util,
                "status": budget_status,
            },
            "caching": {
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "hit_rate_pct": hit_rate,
                "estimated_cost_saved_inr": round(self.estimated_savings_inr, 2),
            },
        }


# Global Cost Controller Singleton
_GLOBAL_COST_CONTROLLER = CostController()


def get_cost_controller() -> CostController:
    return _GLOBAL_COST_CONTROLLER
