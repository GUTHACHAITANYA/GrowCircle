"""
GrowCircle Human Feedback Loop & Evaluation Hardening (ML-7).

Allows users to mark an AI/model answer "wrong" with:
- IVR single keypress (Key 9 or 0)
- WhatsApp "WRONG_ANSWER" button or voice note
- Web/PWA "Flag as Incorrect" button

Flagged items enter an agronomist/ML review queue and get promoted
directly into golden evaluation test sets for CI regression defense.
"""

from __future__ import annotations

import datetime
import json
import logging
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ml.agent.safety import SafetyGuardrails

logger = logging.getLogger(__name__)


@dataclass
class NegativeFeedbackRecord:
    """Structure for user-reported incorrect answer."""

    feedback_id: str
    user_id: str | int
    channel: str  # ivr, whatsapp, web
    category: str  # price_error, forecast_error, vision_error, agent_voice_error, logistics_error
    query_text: str
    model_response: str
    farmer_correction: str | None
    created_at: str
    status: str  # pending_review, promoted_to_eval, dismissed
    reviewer_notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HumanFeedbackLoop:
    """
    Manages user error reports, review queues, and promotion into CI evaluation datasets.
    """

    def __init__(self, storage_path: str = "data/feedback/human_eval_cases.json") -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._queue: list[NegativeFeedbackRecord] = []
        self._promoted_eval_cases: list[dict[str, Any]] = []
        self._load_persisted_eval_cases()

    def record_wrong_answer(
        self,
        user_id: str | int,
        channel: str,
        category: str,
        query_text: str,
        model_response: str,
        farmer_correction: str | None = None,
    ) -> dict[str, Any]:
        """
        Captures a 1-click or 1-key error flag from a farmer/buyer.
        Redacts PII from user text before queueing.
        """
        # Redact any phone numbers or Aadhaar digits from query and correction
        sanitized_query = SafetyGuardrails.redact_pii(query_text)
        sanitized_correction = SafetyGuardrails.redact_pii(farmer_correction) if farmer_correction else None

        fb_id = f"fb-err-{uuid.uuid4().hex[:6]}"
        rec = NegativeFeedbackRecord(
            feedback_id=fb_id,
            user_id=str(user_id),
            channel=channel,
            category=category,
            query_text=sanitized_query,
            model_response=model_response,
            farmer_correction=sanitized_correction,
            created_at=datetime.datetime.now(datetime.UTC).isoformat(),
            status="pending_review",
        )
        self._queue.append(rec)

        logger.info(
            "User %s flagged answer as incorrect via %s (%s). Feedback ID: %s",
            user_id,
            channel,
            category,
            fb_id,
        )

        return {
            "status": "queued_for_review",
            "feedback_id": fb_id,
            "message": (
                "మీ సమాచారానికి ధన్యవాదాలు. GrowCircle సాంకేతిక నిపుణులు దీనిని సమీక్షిస్తారు. "
                "(Thank you; our team will review this error report to improve future responses.)"
            ),
        }

    def get_review_queue(self, status_filter: str | None = None) -> list[dict[str, Any]]:
        """Returns records in review queue, optionally filtered by status."""
        items = self._queue
        if status_filter:
            items = [r for r in items if r.status == status_filter]
        return [r.to_dict() for r in reversed(items)]

    def review_and_resolve(
        self,
        feedback_id: str,
        action: str,  # promote_to_eval, dismiss
        reviewer_notes: str | None = None,
    ) -> dict[str, Any]:
        """
        Agronomist/Engineer reviews user report.
        If 'promote_to_eval', item is transformed into a golden test case for CI test harness.
        """
        rec = next((r for r in self._queue if r.feedback_id == feedback_id), None)
        if not rec:
            raise KeyError(f"Feedback ID '{feedback_id}' not found.")

        rec.reviewer_notes = reviewer_notes

        if action == "promote_to_eval":
            rec.status = "promoted_to_eval"

            # Transform into golden test case
            eval_case = {
                "case_id": f"GOLDEN-{rec.feedback_id.upper()}",
                "origin": f"human_feedback_{rec.channel}",
                "category": rec.category,
                "input_utterance": rec.query_text,
                "flagged_response": rec.model_response,
                "expected_behavior": rec.farmer_correction or "Certified verified ground truth",
                "promoted_at": datetime.datetime.now(datetime.UTC).isoformat(),
                "reviewer_notes": reviewer_notes or "Promoted after agronomist verification",
            }
            self._promoted_eval_cases.append(eval_case)
            self._persist_eval_cases()

            logger.info("Feedback %s PROMOTED to evaluation benchmark dataset.", feedback_id)
            return {
                "status": "promoted_to_eval",
                "feedback_id": feedback_id,
                "case_id": eval_case["case_id"],
                "message": "Error report verified and converted into golden regression test case.",
            }

        elif action == "dismiss":
            rec.status = "dismissed"
            logger.info("Feedback %s dismissed by reviewer.", feedback_id)
            return {
                "status": "dismissed",
                "feedback_id": feedback_id,
                "message": "Report reviewed and dismissed.",
            }

        else:
            raise ValueError(f"Unknown review action: '{action}'. Choose 'promote_to_eval' or 'dismiss'.")

    def get_promoted_eval_cases(self) -> list[dict[str, Any]]:
        """Returns all golden test cases derived from human feedback."""
        return list(self._promoted_eval_cases)

    def _persist_eval_cases(self) -> None:
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self._promoted_eval_cases, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning("Failed to persist human eval cases to disk: %s", e)

    def _load_persisted_eval_cases(self) -> None:
        if self.storage_path.exists():
            try:
                with open(self.storage_path, encoding="utf-8") as f:
                    self._promoted_eval_cases = json.load(f)
            except Exception as e:
                logger.debug("Could not read existing eval cases file: %s", e)


# Global Human Feedback Singleton
_GLOBAL_FEEDBACK_LOOP = HumanFeedbackLoop()


def get_feedback_loop() -> HumanFeedbackLoop:
    return _GLOBAL_FEEDBACK_LOOP
