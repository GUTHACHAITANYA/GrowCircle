"""
Language and Localization API routes.
Provides honest coverage status across all 22 scheduled Indian languages plus English,
per-language coverage report, and user profile language preferences.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_async_db
from backend.app.models.language import Language
from backend.app.models.user import User
from backend.app.services.language_data import ALL_LANGUAGES, SUPPORTED_LANGUAGE_CODES
from backend.app.services.security import get_optional_current_user

router = APIRouter(prefix="/languages", tags=["Languages & Localization"])


class LanguageOut(BaseModel):
    code: str
    name_en: str
    name_native: str
    script: str
    is_rtl: bool
    ui_ready: bool
    voice_stt_ready: bool
    voice_tts_ready: bool
    reviewed_by_native_speaker: bool
    fallback_code: str


class UpdateLanguageRequest(BaseModel):
    language: str = Field(description="ISO 639 language code for one of the 23 supported languages")
    phone: str | None = Field(default=None, description="Optional phone number to update if not using JWT")


async def _ensure_languages_seeded(db: AsyncSession) -> None:
    """Auto-seeds the languages table if it is currently empty."""
    existing_count = await db.scalar(select(Language.code).limit(1))
    if not existing_count:
        for item in ALL_LANGUAGES:
            lang = Language(**item)
            db.add(lang)
        await db.commit()


@router.get("", response_model=list[LanguageOut])
async def list_languages(db: AsyncSession = Depends(get_async_db)) -> list[LanguageOut]:
    """
    Returns the list of all 22 scheduled languages plus English with honest coverage fields:
    ui_ready, voice_stt_ready, voice_tts_ready, reviewed_by_native_speaker, fallback_code.
    """
    await _ensure_languages_seeded(db)
    result = await db.scalars(select(Language))
    db_langs = list(result.all())

    # Ensure returned order matches standard ALL_LANGUAGES
    lang_map = {l.code: l for l in db_langs}
    output = []
    for item in ALL_LANGUAGES:
        code = item["code"]
        if code in lang_map:
            l = lang_map[code]
            output.append(
                LanguageOut(
                    code=l.code,
                    name_en=l.name_en,
                    name_native=l.name_native,
                    script=l.script,
                    is_rtl=l.is_rtl,
                    ui_ready=l.ui_ready,
                    voice_stt_ready=l.voice_stt_ready,
                    voice_tts_ready=l.voice_tts_ready,
                    reviewed_by_native_speaker=l.reviewed_by_native_speaker,
                    fallback_code=l.fallback_code,
                )
            )
        else:
            output.append(LanguageOut(**item))
    return output


@router.patch("/preference")
async def update_user_language_preference(
    req: UpdateLanguageRequest,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """
    Updates the language choice in the user profile when logged in (or by phone).
    This unified preference is shared across IVR, WhatsApp, and Web.
    """
    code = req.language.strip().lower()
    if code not in SUPPORTED_LANGUAGE_CODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Language code '{code}' is not supported. Supported: {sorted(SUPPORTED_LANGUAGE_CODES)}",
        )

    target_user: User | None = current_user
    if not target_user and req.phone:
        clean_phone = req.phone.strip().replace(" ", "").replace("+", "")
        target_user = await db.scalar(select(User).where(User.phone.contains(clean_phone)))

    if not target_user:
        return {
            "status": "guest",
            "language": code,
            "message": "User not authenticated or phone not found. Store in cookie/local storage.",
        }

    target_user.language = code
    await db.commit()

    return {
        "status": "success",
        "user_id": target_user.id,
        "phone": target_user.phone,
        "language": target_user.language,
        "message": "Language preference updated across Web, IVR, and WhatsApp.",
    }


@router.get("/coverage-report")
async def get_coverage_report(db: AsyncSession = Depends(get_async_db)) -> dict[str, Any]:
    """
    Produces the per-language honest coverage report:
    Shows ui_ready, voice_stt_ready, voice_tts_ready, reviewed_by_native_speaker,
    and untranslated/fallback behavior for each language.
    """
    await _ensure_languages_seeded(db)
    result = await db.scalars(select(Language))
    db_langs = {l.code: l for l in result.all()}

    report: list[dict[str, Any]] = []
    for item in ALL_LANGUAGES:
        code = item["code"]
        model = db_langs.get(code)
        ui_ready = model.ui_ready if model else item["ui_ready"]
        reviewed = model.reviewed_by_native_speaker if model else item["reviewed_by_native_speaker"]
        stt = model.voice_stt_ready if model else item["voice_stt_ready"]
        tts = model.voice_tts_ready if model else item["voice_tts_ready"]
        fallback = model.fallback_code if model else item["fallback_code"]

        report.append(
            {
                "code": code,
                "name_en": item["name_en"],
                "name_native": item["name_native"],
                "ui_ready": ui_ready,
                "reviewed_by_native_speaker": reviewed,
                "voice_stt_ready": stt,
                "voice_tts_ready": tts,
                "status": "Fully translated & reviewed" if (ui_ready and reviewed) else "Partly translated (machine draft)",
                "fallback_per_string_to": fallback,
            }
        )

    return {
        "total_languages": len(report),
        "scheduled_languages_count": 22,
        "english_included": True,
        "fully_reviewed_languages": [r["code"] for r in report if r["reviewed_by_native_speaker"]],
        "partly_translated_languages": [r["code"] for r in report if not r["reviewed_by_native_speaker"]],
        "languages": report,
    }
