"""
FastAPI route handlers for Consumer features: crop catalog,
seasonality analysis ("Is it expensive this month?"), and price alerts.
No login required for viewing or subscribing.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_async_db
from backend.app.schemas.consumer import (
    CropOut,
    PriceAlertCreate,
    PriceAlertOut,
    SeasonalityAnalysis,
)
from backend.app.services.consumer_service import ConsumerService

router = APIRouter(prefix="/consumer", tags=["Consumer"])


@router.get("/crops", response_model=list[CropOut])
async def list_consumer_crops(
    db: AsyncSession = Depends(get_async_db),
) -> list[CropOut]:
    """
    Returns available fruit & vegetable crops with multilingual names.
    No login required.
    """
    return await ConsumerService.get_all_crops(db)


@router.get("/seasonality", response_model=SeasonalityAnalysis)
async def get_crop_seasonality(
    crop: Annotated[str, Query(description="Crop slug, e.g. 'banana', 'tomato'")] = "banana",
    district: Annotated[str, Query(description="District name")] = "Guntur",
    db: AsyncSession = Depends(get_async_db),
) -> SeasonalityAnalysis:
    """
    Answers: 'Is it expensive this month?'
    Evaluates current modal price against benchmark seasonal baseline
    and provides plain-language affordability guidance.
    No login required.
    """
    return await ConsumerService.analyze_seasonality(db, crop_id=crop, district=district)


@router.post("/alerts", response_model=PriceAlertOut, status_code=status.HTTP_201_CREATED)
async def subscribe_price_alert(
    alert_in: PriceAlertCreate,
    db: AsyncSession = Depends(get_async_db),
) -> PriceAlertOut:
    """
    Subscribes a consumer or household for WhatsApp / Telegram price alerts.
    No login required.
    """
    return await ConsumerService.create_alert(db, alert_in)


@router.get("/alerts", response_model=list[PriceAlertOut])
async def list_consumer_alerts(
    phone: Annotated[str, Query(description="Consumer phone number")],
    db: AsyncSession = Depends(get_async_db),
) -> list[PriceAlertOut]:
    """Lists active alerts for the given phone number."""
    return await ConsumerService.list_user_alerts(db, phone)


@router.delete("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_consumer_alert(
    alert_id: int,
    phone: Annotated[str, Query(description="Consumer phone number")],
    db: AsyncSession = Depends(get_async_db),
) -> None:
    """Unsubscribes / cancels a price alert."""
    success = await ConsumerService.delete_alert(db, alert_id, phone)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found or unauthorized")
