"""
Feedback API router supporting web form, voice note URL, and IVR keypress feedback.
"""

from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_async_db
from backend.app.models.feedback import Feedback
from backend.app.services.security import require_admin_role_enforced

router = APIRouter(prefix="/feedback", tags=["Pilot Kit Feedback"])


class FeedbackCreate(BaseModel):
    user_id: int | None = None
    channel: str = Field(default="web", pattern="^(web|ivr|whatsapp)$")
    phone: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    category: str = Field(default="general", max_length=50)
    message: str | None = Field(default=None, max_length=1000)
    voice_audio_url: str | None = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    payload: FeedbackCreate,
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Captures pilot user feedback across web, voice note, or IVR keypress."""
    # Mask phone if provided for privacy
    masked_phone = None
    if payload.phone:
        p = payload.phone.strip()
        masked_phone = f"{p[:3]}XXXX{p[-3:]}" if len(p) >= 6 else "XXXXXX"

    fb = Feedback(
        user_id=payload.user_id,
        channel=payload.channel,
        phone=masked_phone,
        rating=payload.rating,
        category=payload.category,
        message=payload.message,
        voice_audio_url=payload.voice_audio_url,
    )
    db.add(fb)
    await db.commit()
    await db.refresh(fb)

    return {
        "status": "success",
        "feedback_id": fb.id,
        "channel": fb.channel,
        "message": "Thank you for helping us improve GrowCircle for everyone in the circle.",
    }


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_admin_role_enforced())],
)
async def list_feedback(
    limit: int = 50,
    db: AsyncSession = Depends(get_async_db),
) -> list[dict[str, Any]]:

    """Administrative inspection of pilot user feedback."""
    res = await db.execute(select(Feedback).order_by(Feedback.created_at.desc()).limit(limit))
    feedbacks = res.scalars().all()
    return [
        {
            "id": f.id,
            "channel": f.channel,
            "rating": f.rating,
            "category": f.category,
            "message": f.message,
            "voice_audio_url": f.voice_audio_url,
            "created_at": f.created_at.isoformat(),
        }
        for f in feedbacks
    ]
