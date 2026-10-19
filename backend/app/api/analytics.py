"""
Analytics API router exposing privacy-friendly platform metrics across all doors.
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_async_db
from backend.app.services.analytics_service import get_privacy_friendly_analytics

router = APIRouter(prefix="/analytics", tags=["Privacy-Friendly Platform Analytics"])


@router.get("/dashboard")
async def get_analytics_dashboard(
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Returns aggregated non-PII operational analytics across all 5 doors."""
    return await get_privacy_friendly_analytics(db)
