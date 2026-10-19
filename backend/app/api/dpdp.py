"""
DPDP Act 2023 API router: Grievance Officer details, Consent, Data Export, and Account Deletion.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.rate_limit import get_client_ip, rate_limit_check
from backend.app.db.session import get_async_db
from backend.app.models.user import User
from backend.app.services.dpdp_service import (
    GRIEVANCE_OFFICER_INFO,
    delete_user_account,
    export_user_data,
    record_user_consent,
)
from backend.app.services.security import get_optional_current_user

router = APIRouter(prefix="/dpdp", tags=["DPDP Act 2023 Compliance"])


def _verify_dpdp_caller_authorization(target_user_id: int, current_user: User | None) -> None:
    """Enforces that callers can only access or delete their own data under DPDP Act."""
    if settings.ENVIRONMENT in ("production", "staging"):
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required for DPDP principal data operations.",
            )
        if current_user.id != target_user_id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: You cannot access or modify another user's personal data.",
            )
    else:
        # In development/test environments, check ownership if authenticated token is supplied
        if current_user and current_user.id != target_user_id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: You cannot access or modify another user's personal data.",
            )


class ConsentRequest(BaseModel):
    user_id: int
    version: str = "1.0"
    purpose: str = "mandi_prices_and_marketplace"


class DeletionRequest(BaseModel):
    user_id: int
    reason: str = Field(default="User requested account closure", max_length=500)


@router.get("/grievance")
async def get_grievance_contact() -> dict[str, Any]:
    """Returns statutory Data Protection Officer & Grievance Redressal details under DPDP Act 2023."""
    return {
        "status": "active",
        "officer": GRIEVANCE_OFFICER_INFO,
    }


@router.post("/consent")
async def grant_consent(
    payload: ConsentRequest,
    request: Request,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Records explicit consent under Section 6 of DPDP Act."""
    _verify_dpdp_caller_authorization(payload.user_id, current_user)
    client_ip = get_client_ip(request)
    try:
        user = await record_user_consent(
            db=db,
            user_id=payload.user_id,
            version=payload.version,
            purpose=payload.purpose,
            client_ip=client_ip,
        )
        return {
            "status": "consent_recorded",
            "user_id": user.id,
            "consent_at": user.consent_at.isoformat() if user.consent_at else None,
            "version": user.consent_version,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/export")
async def export_my_data(
    user_id: int,
    request: Request,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Provides complete portable data package under Section 11 of DPDP Act."""
    _verify_dpdp_caller_authorization(user_id, current_user)
    client_ip = get_client_ip(request)
    # Rate limit exports to prevent scraping
    await rate_limit_check("dpdp_export", str(user_id), max_requests=5, window_seconds=3600)

    try:
        return await export_user_data(db=db, user_id=user_id, client_ip=client_ip)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post("/delete-account")
async def request_account_deletion(
    payload: DeletionRequest,
    request: Request,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Right to Erasure under Section 12 of DPDP Act. Anonymizes personal records."""
    _verify_dpdp_caller_authorization(payload.user_id, current_user)
    client_ip = get_client_ip(request)
    try:
        return await delete_user_account(
            db=db,
            user_id=payload.user_id,
            reason=payload.reason,
            client_ip=client_ip,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

