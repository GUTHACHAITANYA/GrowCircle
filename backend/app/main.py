"""
GrowCircle Core Engine - FastAPI Modular Monolith.
"One engine, five doors".
Production hardened with OWASP security headers, Prometheus metrics, and DPDP governance.
"""

import logging
import uuid
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.core.config import settings
from backend.app.core.monitoring import (
    PrometheusMiddleware,
    init_sentry,
    metrics_registry,
)
from backend.app.core.security_headers import SecurityHeadersMiddleware

logger = logging.getLogger(__name__)


def _sync_sqlite_schema(sync_conn) -> None:
    """Ensure SQLite schema has all User auth & security columns for local development."""
    try:
        cur = sync_conn.connection.cursor()
        cur.execute("PRAGMA table_info(users)")
        cols = {row[1] for row in cur.fetchall()}
        if cols:
            additions = [
                ("name", "VARCHAR(100)"),
                ("session_version", "INTEGER NOT NULL DEFAULT 1"),
                ("is_admin_2fa_verified", "BOOLEAN NOT NULL DEFAULT 0"),
                ("failed_otp_attempts", "INTEGER NOT NULL DEFAULT 0"),
                ("locked_until", "DATETIME"),
            ]
            for col_name, col_type in additions:
                if col_name not in cols:
                    cur.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
    except Exception as e:
        logger.warning(f"SQLite schema sync warning: {e}")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    init_sentry()
    if "sqlite" in settings.DATABASE_URL:
        from backend.app.db.base import Base
        import backend.app.models  # noqa: F401
        from backend.app.db.session import async_engine

        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(_sync_sqlite_schema)

    # RULE A & Requirement 6: Production startup check
    # In production, seed or mock prices (source='demo') must be impossible to load.
    if settings.APP_MODE == "production":
        from sqlalchemy import func, select
        from backend.app.db.session import async_engine
        from backend.app.models.price import Price

        engine_to_use = getattr(_app.state, "engine", None) or async_engine
        async with engine_to_use.connect() as conn:
            demo_count = (
                await conn.execute(
                    select(func.count(Price.id)).where(Price.source == "demo")
                )
            ).scalar() or 0

            if demo_count > 0:
                raise RuntimeError(
                    f"PRODUCTION STARTUP REFUSAL: Found {demo_count} price rows with source='demo'. "
                    "Production mode strictly forbids demo data. Purge seed data before starting."
                )

    yield


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assigns unique request ID for tracing and error reporting."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = req_id
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response


app = FastAPI(
    title="GrowCircle API",
    description="Unified single-source-of-truth engine powering Phone/IVR, WhatsApp bot, Web/PWA, Mobile, and Admin.",
    version="1.0.0",
    lifespan=lifespan,
)

# Global unhandled exception handler returning structured JSON with request_id (no bare 500s)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    req_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    logger.error(f"[SERVER_ERROR] [req_id={req_id}] Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Something went wrong on our side",
            "code": "INTERNAL_SERVER_ERROR",
            "request_id": req_id,
        },
        headers={"X-Request-ID": req_id},
    )

# 0. Request ID Middleware
app.add_middleware(RequestIdMiddleware)

# 1. OWASP Top-10 Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# 2. Prometheus Observability Metrics Middleware
app.add_middleware(PrometheusMiddleware)

# 3. CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

from backend.app.api.admin_anomalies import router as admin_anomalies_router
from backend.app.api.agent import router as agent_router
from backend.app.api.analytics import router as analytics_router
from backend.app.api.auth import router as auth_router
from backend.app.api.consumer import router as consumer_router
from backend.app.api.crop_planning import router as crop_planning_router
from backend.app.api.diary import router as diary_router
from backend.app.api.dpdp import router as dpdp_router
from backend.app.api.data_health import router as data_health_router
from backend.app.api.feedback import router as feedback_router
from backend.app.api.forecast import router as forecast_router
from backend.app.api.ground_truth import router as ground_truth_router
from backend.app.api.ivr import router as ivr_router
from backend.app.api.languages import router as languages_router
from backend.app.api.mandi_master_admin import router as mandi_master_admin_router
from backend.app.api.market import router as market_router
from backend.app.api.monitoring import router as monitoring_router
from backend.app.api.routes import router as api_router
from backend.app.api.smart_logistics import router as smart_logistics_router
from backend.app.api.transport import router as transport_router
from backend.app.api.vision import router as vision_router
from backend.app.api.whatsapp import router as whatsapp_router
# 4. Mount Door Routers
app.include_router(auth_router)
app.include_router(api_router)
app.include_router(ivr_router)
app.include_router(whatsapp_router)
app.include_router(market_router)
app.include_router(transport_router)
app.include_router(diary_router)
app.include_router(consumer_router)
app.include_router(dpdp_router)
app.include_router(feedback_router)
app.include_router(analytics_router)
app.include_router(forecast_router, tags=["Forecasting"])
app.include_router(crop_planning_router, tags=["Crop Planning"])
app.include_router(vision_router)
app.include_router(admin_anomalies_router)
app.include_router(smart_logistics_router)
app.include_router(agent_router)
app.include_router(monitoring_router)
app.include_router(data_health_router)
app.include_router(ground_truth_router)
app.include_router(mandi_master_admin_router)
app.include_router(languages_router)


# 5. Prometheus Metrics Endpoint
@app.get("/metrics", tags=["Observability"])
async def get_metrics() -> Response:
    """Exposes standard Prometheus text metrics for Prometheus / Grafana scraping."""
    return Response(
        content=metrics_registry.generate_prometheus_text(),
        media_type="text/plain; version=0.0.4",
    )
