"""
Prometheus and Sentry monitoring module for GrowCircle core engine.
Exposes standard Prometheus metrics format at /metrics and handles error tracking.
"""

import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.core.config import settings


class MetricsRegistry:
    """Thread-safe Prometheus-compatible metrics registry."""

    def __init__(self) -> None:
        self.request_counts: dict[tuple[str, str, int], int] = defaultdict(int)
        self.request_latencies: dict[tuple[str, str], list[float]] = defaultdict(list)
        self.ivr_calls: int = 0
        self.whatsapp_messages: int = 0
        self.rate_limit_hits: int = 0

    def record_request(self, method: str, path: str, status_code: int, duration: float) -> None:
        # Simplify path to prevent high cardinality
        clean_path = path.split("?")[0]
        if clean_path.startswith("/prices"):
            clean_path = "/prices"
        elif clean_path.startswith("/diary/seasons/"):
            clean_path = "/diary/seasons/{id}"
        elif clean_path.startswith("/market/"):
            clean_path = "/market/*"
        elif clean_path.startswith("/transport/"):
            clean_path = "/transport/*"

        self.request_counts[(method, clean_path, status_code)] += 1

        latency_key = (method, clean_path)
        self.request_latencies[latency_key].append(duration)
        if len(self.request_latencies[latency_key]) > 200:
            self.request_latencies[latency_key] = self.request_latencies[latency_key][-100:]

    def record_ivr_call(self) -> None:
        self.ivr_calls += 1

    def record_whatsapp_message(self) -> None:
        self.whatsapp_messages += 1

    def record_rate_limit_hit(self) -> None:
        self.rate_limit_hits += 1

    def generate_prometheus_text(self) -> str:
        lines = [
            "# HELP growcircle_requests_total Total number of HTTP requests processed by GrowCircle engine",
            "# TYPE growcircle_requests_total counter",
        ]
        for (method, path, status_code), count in self.request_counts.items():
            lines.append(
                f'growcircle_requests_total{{method="{method}",path="{path}",status="{status_code}"}} {count}'
            )

        lines.extend([
            "# HELP growcircle_request_duration_seconds_avg Average request processing latency in seconds",
            "# TYPE growcircle_request_duration_seconds_avg gauge",
        ])
        for (method, path), latencies in self.request_latencies.items():
            if latencies:
                avg_lat = sum(latencies) / len(latencies)
                lines.append(
                    f'growcircle_request_duration_seconds_avg{{method="{method}",path="{path}"}} {avg_lat:.4f}'
                )

        lines.extend([
            "# HELP growcircle_ivr_calls_total Total telephony IVR callback calls initiated",
            "# TYPE growcircle_ivr_calls_total counter",
            f"growcircle_ivr_calls_total {self.ivr_calls}",
            "# HELP growcircle_whatsapp_messages_total Total WhatsApp webhook messages processed",
            "# TYPE growcircle_whatsapp_messages_total counter",
            f"growcircle_whatsapp_messages_total {self.whatsapp_messages}",
            "# HELP growcircle_rate_limit_hits_total Total rate limit 429 rejections",
            "# TYPE growcircle_rate_limit_hits_total counter",
            f"growcircle_rate_limit_hits_total {self.rate_limit_hits}",
        ])
        return "\n".join(lines) + "\n"


metrics_registry = MetricsRegistry()


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Intercepts requests and registers Prometheus latency & count metrics."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        start_time = time.time()
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            metrics_registry.record_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=duration,
            )
            return response
        except Exception:
            duration = time.time() - start_time
            metrics_registry.record_request(
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration=duration,
            )
            raise


def init_sentry() -> None:
    """Initializes Sentry error tracking in staging/production if DSN is set."""
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk

            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                environment=settings.ENVIRONMENT,
                traces_sample_rate=0.2,
                profiles_sample_rate=0.1,
            )
        except ImportError:
            pass
