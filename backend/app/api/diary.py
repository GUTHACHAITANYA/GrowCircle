"""
FastAPI route handlers for Farm Diary, economic metrics, voice read-back, and data export.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.db.session import get_async_db
from backend.app.models.farm_diary import FarmDiaryEntry, FarmSeason
from backend.app.models.user import User
from backend.app.schemas.diary import (
    FarmDiaryEntryCreate,
    FarmDiaryEntryOut,
    FarmDiaryEntryVoiceInput,
    FarmSeasonCreate,
    FarmSeasonOut,
    SeasonFinancialMetrics,
    VoiceConfirmationReadBack,
)
from backend.app.services.diary_service import FarmDiaryService
from backend.app.services.security import get_optional_current_user

router = APIRouter(prefix="/diary", tags=["Farm Diary"])


def _verify_season_access(season: FarmSeason, current_user: User | None) -> None:
    """Verifies that caller owns the cultivation season records."""
    if settings.ENVIRONMENT in ("production", "staging"):
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to access farm diary",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if current_user.role != "admin" and current_user.id != season.farmer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot access another farmer's diary season",
            )
    else:
        if current_user and current_user.role != "admin" and current_user.id != season.farmer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot access another farmer's diary season",
            )


@router.post("/seasons", response_model=FarmSeasonOut, status_code=status.HTTP_201_CREATED)
async def create_season(
    season_in: FarmSeasonCreate,
    farmer_id: Annotated[int, Query(description="Farmer user ID")] = 1,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> FarmSeasonOut:
    """Creates a new farm plot season / cultivation cycle."""
    if settings.ENVIRONMENT in ("production", "staging"):
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to create farm diary season",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if current_user.role != "admin":
            farmer_id = current_user.id
    else:
        if current_user and current_user.role != "admin":
            farmer_id = current_user.id

    # Ensure user exists or fallback
    user = await db.scalar(select(User).where(User.id == farmer_id))
    if not user:
        # Create lightweight placeholder if not present
        user = User(id=farmer_id, phone="+919848011223", role="farmer", district="Guntur")
        db.add(user)
        await db.commit()

    season = FarmSeason(
        farmer_id=farmer_id,
        season_name=season_in.season_name,
        crop_id=season_in.crop_id.lower().strip(),
        area_acres=season_in.area_acres,
        soil_type=season_in.soil_type,
        planting_date=season_in.planting_date,
        harvest_date=season_in.harvest_date,
        expected_yield_kg=season_in.expected_yield_kg,
        district=season_in.district,
    )
    db.add(season)
    await db.commit()
    await db.refresh(season)
    return FarmSeasonOut.model_validate(season)


@router.get("/seasons", response_model=list[FarmSeasonOut])
async def list_seasons(
    farmer_id: Annotated[int, Query(description="Farmer user ID")] = 1,
    db: AsyncSession = Depends(get_async_db),
) -> list[FarmSeasonOut]:
    """Lists seasons for a farmer."""
    result = await db.execute(
        select(FarmSeason)
        .where(FarmSeason.farmer_id == farmer_id)
        .order_by(desc(FarmSeason.planting_date))
    )
    seasons = result.scalars().all()
    return [FarmSeasonOut.model_validate(s) for s in seasons]


@router.get("/seasons/{season_id}", response_model=FarmSeasonOut)
async def get_season(
    season_id: int,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> FarmSeasonOut:
    """Gets details for a single farm season."""
    season = await db.scalar(select(FarmSeason).where(FarmSeason.id == season_id))
    if not season:
        raise HTTPException(status_code=404, detail="FarmSeason not found")
    _verify_season_access(season, current_user)
    return FarmSeasonOut.model_validate(season)


@router.post("/voice-readback", response_model=VoiceConfirmationReadBack)
async def generate_voice_readback(
    voice_input: FarmDiaryEntryVoiceInput,
) -> VoiceConfirmationReadBack:
    """
    Parses spoken voice notes and generates read-back confirmation strings
    in English, Telugu, Hindi, and Gujarati before saving.
    """
    return FarmDiaryService.parse_voice_entry(
        transcript=voice_input.voice_transcript_text,
        entry_date=voice_input.entry_date,
    )


@router.post(
    "/seasons/{season_id}/entries",
    response_model=FarmDiaryEntryOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_diary_entry(
    season_id: int,
    entry_in: FarmDiaryEntryCreate,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> FarmDiaryEntryOut:
    """Adds a verified entry (cost, yield log, or sale revenue) to the season ledger."""
    season = await db.scalar(select(FarmSeason).where(FarmSeason.id == season_id))
    if not season:
        raise HTTPException(status_code=404, detail="FarmSeason not found")
    _verify_season_access(season, current_user)

    entry = FarmDiaryEntry(
        season_id=season_id,
        entry_type=entry_in.entry_type,
        category=entry_in.category,
        amount_inr=entry_in.amount_inr,
        quantity_kg=entry_in.quantity_kg,
        unit_price_inr=entry_in.unit_price_inr,
        entry_date=entry_in.entry_date,
        notes=entry_in.notes,
        voice_raw_text=entry_in.voice_raw_text,
        readback_confirmed=entry_in.readback_confirmed,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return FarmDiaryEntryOut.model_validate(entry)


@router.get("/seasons/{season_id}/entries", response_model=list[FarmDiaryEntryOut])
async def list_season_entries(
    season_id: int,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> list[FarmDiaryEntryOut]:
    """Lists all ledger entries for a season."""
    season = await db.scalar(select(FarmSeason).where(FarmSeason.id == season_id))
    if not season:
        raise HTTPException(status_code=404, detail="FarmSeason not found")
    _verify_season_access(season, current_user)

    result = await db.execute(
        select(FarmDiaryEntry)
        .where(FarmDiaryEntry.season_id == season_id)
        .order_by(desc(FarmDiaryEntry.entry_date))
    )
    entries = result.scalars().all()
    return [FarmDiaryEntryOut.model_validate(e) for e in entries]


@router.get("/seasons/{season_id}/metrics", response_model=SeasonFinancialMetrics)
async def get_season_financial_metrics(
    season_id: int,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> SeasonFinancialMetrics:
    """
    Returns full season economics: Profit/Loss per acre, break-even price,
    cost breakdown, and actual vs Mandi average sale price comparison.
    """
    season = await db.scalar(select(FarmSeason).where(FarmSeason.id == season_id))
    if not season:
        raise HTTPException(status_code=404, detail="FarmSeason not found")
    _verify_season_access(season, current_user)

    try:
        return await FarmDiaryService.calculate_season_metrics(db, season_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/seasons/{season_id}/export")
async def export_season_records(
    season_id: int,
    format: Annotated[str, Query(description="'csv' or 'json'")] = "csv",
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> Response:
    """
    Exports the farmer's own diary records on request in CSV or JSON.
    Guarantees DPDP Act data portability.
    """
    season = await db.scalar(select(FarmSeason).where(FarmSeason.id == season_id))
    if not season:
        raise HTTPException(status_code=404, detail="FarmSeason not found")
    _verify_season_access(season, current_user)

    if format.lower() == "csv":
        csv_data = await FarmDiaryService.export_season_records_csv(db, season_id)
        filename = f"growcircle_diary_season_{season_id}.csv"
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    else:
        metrics = await FarmDiaryService.calculate_season_metrics(db, season_id)
        return Response(
            content=metrics.model_dump_json(indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=growcircle_diary_{season_id}.json"
            },
        )
