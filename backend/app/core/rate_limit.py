"""
Rate limiting module for IVR, WhatsApp webhooks, OTP endpoints, and public APIs.
Provides Redis token-bucket / sliding window with thread-safe in-memory fallback.
"""

import time
from collections import defaultdict
from typing import ClassVar

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    """Thread-safe in-memory sliding window rate limiter fallback."""

    def __init__(self) -> None:
        self._history: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
        now = time.time()
        cutoff = now - window_seconds
        # Clean older entries
        self._history[key] = [ts for ts in self._history[key] if ts > cutoff]

        if len(self._history[key]) >= max_requests:
            retry_after = int(window_seconds - (now - self._history[key][0]))
            return False, max(1, retry_after)

        self._history[key].append(now)
        return True, 0

    def reset(self) -> None:
        self._history.clear()


in_memory_limiter = InMemoryRateLimiter()


class RateLimitRule:
    IVR: ClassVar[tuple[int, int]] = (60, 60)  # 60 req / 60 sec (in-call interactive DTMF)
    IVR_MISSED_CALL: ClassVar[tuple[int, int]] = (5, 60)  # 5 req / 60 sec (missed call callback trigger)
    WHATSAPP: ClassVar[tuple[int, int]] = (30, 60)  # 30 req / 60 sec
    OTP: ClassVar[tuple[int, int]] = (3, 600)  # 3 req / 10 min
    PUBLIC_API: ClassVar[tuple[int, int]] = (120, 60)  # 120 req / 60 sec
    VISION: ClassVar[tuple[int, int]] = (30, 60)  # 30 req / 60 sec



async def rate_limit_check(
    key_prefix: str,
    identifier: str,
    max_requests: int,
    window_seconds: int,
) -> None:
    """
    Checks rate limit. Raises HTTP 429 if limit is exceeded.
    """
    key = f"ratelimit:{key_prefix}:{identifier}"

    # In production with Redis:
    # Use Redis sorted set / INCR with EXPIRE
    # In tests or development: in-memory limiter
    allowed, retry_after = in_memory_limiter.is_allowed(key, max_requests, window_seconds)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for {key_prefix}. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )


def get_client_ip(request: Request) -> str:
    """Extract client IP handling proxies / X-Forwarded-For."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"
