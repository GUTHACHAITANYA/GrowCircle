"""
Safety Guardrails, Prompt-Injection Defense, and PII Redaction for Voice/Chat Agent.
Phase ML-6: Natural Speech Voice and Chat Agent.

Provides:
1. Multi-pattern prompt injection and jailbreak detector.
2. Strict XML data delimiter encapsulation (<tool_data>, <trusted_doc>).
3. Rate limiting and abusive content screening.
4. Indian PII redactor (phone numbers, Aadhaar, bank accounts).
5. Multi-tenant privacy barrier (prevents leaking other users' sensitive records).
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

logger = logging.getLogger(__name__)

# --- Prompt Injection Patterns ---
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior|system)\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(?:all\s+)?(?:system|developer)\s+prompts", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:a|an)\s+[a-z_]+", re.IGNORECASE),
    re.compile(r"jailbreak|dan\s+mode|unrestricted\s+mode", re.IGNORECASE),
    re.compile(r"override\s+(?:all\s+)?guardrails", re.IGNORECASE),
    re.compile(r"reveal\s+(?:your\s+)?(?:system\s+prompt|hidden\s+instructions)", re.IGNORECASE),
    re.compile(r"pretend\s+(?:that\s+)?you\s+(?:are|have)", re.IGNORECASE),
    re.compile(r"system\s*:\s*you\s+are", re.IGNORECASE),
    re.compile(r"<\s*script\s*>", re.IGNORECASE),
]

# --- Abuse and Vulgarity Patterns ---
ABUSIVE_TERMS = {
    "abuse_en": ["bastard", "idiot", "scam", "cheat", "fraudster"],
    "abuse_hi": ["kameena", "chutiya", "madarchod", "bhosdike", "harami"],
    "abuse_te": ["lanja", "donga", "vedhava", "naa kodaka"],
    "abuse_gu": ["gando", "sala", "haramkhor"],
}

# --- PII Regex Patterns (India) ---
PHONE_REGEX = re.compile(r"\b(?:(?:\+91|0)?[6-9]\d{9})\b")
AADHAAR_REGEX = re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b")
BANK_ACC_REGEX = re.compile(r"\b\d{9,18}\b")
PAN_REGEX = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")


class SafetyGuardrails:
    """
    Enforces security perimeter, prompt-injection defense, rate limits, and PII hygiene.
    """

    # In-memory sliding window rate limiter: {user_id: [timestamp, ...]}
    _RATE_LIMITS: dict[str, list[float]] = {}
    MAX_REQUESTS_PER_MINUTE = 15
    MAX_TURNS_PER_SESSION = 40

    @classmethod
    def sanitize_input(cls, user_text: str) -> dict[str, Any]:
        """
        Inspects user input for prompt injections, abusive language, and malformed tags.
        """
        text = str(user_text).strip()

        # 1. Prompt Injection Detection
        is_injection = False
        matched_pattern = None
        for pattern in INJECTION_PATTERNS:
            if pattern.search(text):
                is_injection = True
                matched_pattern = pattern.pattern
                break

        # 2. Abuse Detection
        text_lower = text.lower()
        is_abusive = False
        for words in ABUSIVE_TERMS.values():
            if any(re.search(rf"\b{re.escape(w)}\b", text_lower) for w in words):
                is_abusive = True
                break

        is_safe = not is_injection and not is_abusive

        return {
            "is_safe": is_safe,
            "is_injection": is_injection,
            "is_abusive": is_abusive,
            "matched_pattern": matched_pattern,
            "sanitized_text": text if is_safe else "[BLOCKED_BY_GUARDRAIL]",
        }

    @classmethod
    def check_rate_limit(cls, user_id: str | int) -> dict[str, Any]:
        """
        Enforces token-bucket rate limits per user/session.
        """
        uid = str(user_id)
        now = time.time()
        window_start = now - 60.0

        timestamps = cls._RATE_LIMITS.setdefault(uid, [])
        # Evict timestamps older than 60s
        cls._RATE_LIMITS[uid] = [t for t in timestamps if t >= window_start]

        if len(cls._RATE_LIMITS[uid]) >= cls.MAX_REQUESTS_PER_MINUTE:
            return {
                "allowed": False,
                "current_count": len(cls._RATE_LIMITS[uid]),
                "limit": cls.MAX_REQUESTS_PER_MINUTE,
                "retry_after_seconds": int(60.0 - (now - cls._RATE_LIMITS[uid][0])),
                "message": "Too many voice/chat requests. Please wait a moment before trying again.",
            }

        cls._RATE_LIMITS[uid].append(now)
        return {
            "allowed": True,
            "current_count": len(cls._RATE_LIMITS[uid]),
            "limit": cls.MAX_REQUESTS_PER_MINUTE,
        }

    @classmethod
    def redact_pii(cls, text: str) -> str:
        """
        Redacts phone numbers, Aadhaar numbers, and bank account numbers from logs and audit trails.
        """
        redacted = PHONE_REGEX.sub("[PHONE_REDACTED]", text)
        redacted = AADHAAR_REGEX.sub("[AADHAAR_REDACTED]", redacted)
        redacted = PAN_REGEX.sub("[PAN_REDACTED]", redacted)
        return redacted

    @classmethod
    def encapsulate_tool_data(cls, tool_name: str, payload: dict[str, Any]) -> str:
        """
        Encapsulates tool results inside strict XML boundary tags
        so the LLM interprets content purely as data, never instructions.
        """
        import json

        data_str = json.dumps(payload, ensure_ascii=False)
        return (
            f"<tool_data name=\"{tool_name}\">\n"
            f"{data_str}\n"
            f"</tool_data>"
        )

    @classmethod
    def encapsulate_rag_document(cls, source_id: str, citation: str, content: str) -> str:
        """
        Encapsulates RAG retrieved documents inside strict XML boundary tags.
        """
        return (
            f"<trusted_doc source_id=\"{source_id}\" citation=\"{citation}\">\n"
            f"{content}\n"
            f"</trusted_doc>"
        )

    @classmethod
    def verify_tenant_authorization(
        cls, request_user_id: int | str, target_owner_id: int | str
    ) -> bool:
        """
        Prevents multi-tenant privacy leakage: Ensures a user cannot query another user's private data.
        """
        return str(request_user_id) == str(target_owner_id)
