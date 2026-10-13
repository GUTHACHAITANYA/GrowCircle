"""
GrowCircle Core Engine - FastAPI Modular Monolith.
"One engine, five doors".
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.ivr import router as ivr_router
from backend.app.api.routes import router as api_router
from backend.app.api.whatsapp import router as whatsapp_router

app = FastAPI(
    title="GrowCircle API",
    description="Unified single-source-of-truth engine powering Phone/IVR, WhatsApp bot, Web/PWA, Mobile, and Admin.",
    version="0.1.0",
)

# Allow CORS for local Next.js development and PWA clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount door routers
app.include_router(api_router)
app.include_router(ivr_router)
app.include_router(whatsapp_router)
