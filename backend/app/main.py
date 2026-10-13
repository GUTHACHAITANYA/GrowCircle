"""
GrowCircle Core Engine - FastAPI Application.
"One engine, five doors".
"""

from typing import Any

from fastapi import FastAPI

app = FastAPI(
    title="GrowCircle API",
    description="One engine powering Phone/IVR, WhatsApp bot, Web/PWA, Mobile app, and Admin panel.",
    version="0.1.0",
)


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, Any]:
    """Health check endpoint for system liveness."""
    return {
        "status": "healthy",
        "service": "growcircle-engine",
        "version": "0.1.0",
        "doors_supported": ["ivr", "whatsapp", "web", "mobile", "admin"],
    }
