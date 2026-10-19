"""
FastAPI Router for Produce Computer Vision Quality & Fraud Checks (Phase ML-4).
Endpoints:
1. POST /vision/inspect: Combined quality grading suggestion + photo fraud check with timeout fallback.
2. POST /vision/fraud-check: Photo integrity check alone (EXIF, GPS, near-duplicate, screenshot Moire).
3. POST /vision/collect: Statutory DPDP-consented photo collection for Label Studio training queue.
"""

from __future__ import annotations

import asyncio
import io
import logging
import time
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from PIL import Image

from backend.app.core.rate_limit import RateLimitRule, get_client_ip, rate_limit_check
from backend.app.schemas.vision import (
    PhotoCollectionResponseSchema,
    PhotoFraudReportSchema,
    QualityInspectionResponseSchema,
)
from ml.vision.collection import VisionDataCollector
from ml.vision.fraud_detection import PhotoFraudChecker
from ml.vision.quality_classifier import ProduceQualityClassifier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vision", tags=["Computer Vision Quality"])

# Singletons
_quality_classifier = ProduceQualityClassifier(confidence_threshold=0.65)
_fraud_checker = PhotoFraudChecker(max_allowed_age_hours=24.0, max_gps_distance_km=25.0)
_data_collector = VisionDataCollector()

MAX_IMAGE_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB maximum produce photo
JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


Image.MAX_IMAGE_PIXELS = 25_000_000  # Cap at 25 MP to neutralize decompression bomb DoS


async def validate_and_read_image(file: UploadFile) -> Image.Image:
    """
    Validates file upload limits and magic bytes before instantiating PIL Image.
    Protects against memory exhaustion DoS, zip-bombs, and invalid payload uploads.
    """
    chunk = await file.read(MAX_IMAGE_UPLOAD_BYTES + 1)
    if len(chunk) > MAX_IMAGE_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Produce photo exceeds maximum allowed size of {MAX_IMAGE_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )
    if len(chunk) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty or corrupted.",
        )

    # Magic byte verification
    if not (chunk.startswith(JPEG_MAGIC) or chunk.startswith(PNG_MAGIC)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image format: File header must match JPEG or PNG magic bytes.",
        )

    try:
        image = Image.open(io.BytesIO(chunk))
        image.load()
        return image.convert("RGB")
    except Image.DecompressionBombError as dbe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image exceeds maximum safe dimensions (decompression bomb detected): {dbe}",
        ) from dbe
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed image binary data: {exc}",
        ) from exc


@router.post("/inspect", response_model=QualityInspectionResponseSchema)
async def inspect_produce_photo(
    request: Request,
    file: UploadFile = File(..., description="JPEG or PNG photograph of the produce lot"),
    crop_id: str = Form("banana", description="'banana' or 'tomato'"),
    listing_id: int | None = Form(None, description="Optional marketplace listing ID"),
    farm_lat: float | None = Form(None, description="Registered farm latitude for GPS verification"),
    farm_lon: float | None = Form(None, description="Registered farm longitude for GPS verification"),
) -> dict[str, Any]:
    """
    Performs remote quality inspection and photo fraud analysis.
    Policy: Only SUGGESTS a grade with confidence. Low confidence returns 'uncertain' and 'buyer to check'.
    Never auto-rejects a farmer.
    Enforces a 3.5-second processing timeout with graceful fallback.
    """
    client_ip = get_client_ip(request)
    await rate_limit_check("vision_inspect", client_ip, *RateLimitRule.VISION)

    start_time = time.perf_counter()

    image = await validate_and_read_image(file)
    logger.info("Inspecting produce image for crop=%s listing=%s", crop_id, listing_id)


    farm_coords = (farm_lat, farm_lon) if (farm_lat is not None and farm_lon is not None) else None

    async def _run_inference() -> tuple[Any, Any]:
        loop = asyncio.get_running_loop()
        # Run CPU-bound image analysis in thread pool
        fraud_rep = await loop.run_in_executor(
            None,
            _fraud_checker.check_photo,
            image,
            farm_coords,
            None,
        )
        quality_res = await loop.run_in_executor(
            None,
            _quality_classifier.assess_quality,
            image,
            crop_id,
        )
        return fraud_rep, quality_res

    try:
        # Enforce 3.5-second processing timeout
        fraud_rep, quality_res = await asyncio.wait_for(_run_inference(), timeout=3.5)
        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        return {
            "crop_id": crop_id.lower().strip(),
            "suggested_grade": quality_res.suggested_grade,
            "confidence": quality_res.confidence,
            "buyer_decision_needed": quality_res.buyer_decision_needed,
            "buyer_guidance_note": quality_res.buyer_guidance_note,
            "ripeness_stage": quality_res.ripeness_stage,
            "ripeness_name": quality_res.ripeness_name,
            "detected_defects": quality_res.detected_defects,
            "grade_probabilities": quality_res.grade_probabilities,
            "human_rule_baseline_grade": quality_res.human_rule_baseline_grade,
            "fraud_report": fraud_rep.to_dict(),
            "latency_ms": elapsed_ms,
            "fallback_triggered": False,
            "policy_notice": "Suggestive only; the buyer retains final inspection and acceptance authority. Farmers are never auto-rejected.",
        }

    except TimeoutError:
        logger.warning("Vision inspection timed out for crop=%s; applying graceful fallback", crop_id)
        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        # Graceful Fallback
        fallback_fraud = _fraud_checker.check_photo(image, farm_coords).to_dict()
        return {
            "crop_id": crop_id.lower().strip(),
            "suggested_grade": "uncertain",
            "confidence": 0.50,
            "buyer_decision_needed": True,
            "buyer_guidance_note": "Inspection processing timed out (> 3.5s); buyer physical check required upon delivery.",
            "ripeness_stage": 4,
            "ripeness_name": "Turning (Unverified)",
            "detected_defects": ["unverified_timeout"],
            "grade_probabilities": {"Grade_A": 0.333, "Grade_B": 0.334, "Grade_C": 0.333},
            "human_rule_baseline_grade": "Grade_B",
            "fraud_report": fallback_fraud,
            "latency_ms": elapsed_ms,
            "fallback_triggered": True,
            "policy_notice": "Suggestive only; the buyer retains final inspection and acceptance authority. Farmers are never auto-rejected.",
        }


@router.post("/fraud-check", response_model=PhotoFraudReportSchema)
async def check_photo_integrity(
    request: Request,
    file: UploadFile = File(..., description="JPEG photograph to evaluate for metadata and screenshot fraud"),
    farm_lat: float | None = Form(None),
    farm_lon: float | None = Form(None),
) -> dict[str, Any]:
    """
    Evaluates EXIF freshness (<24h), GPS coordinates vs registered farm,
    perceptual near-duplicate hashes, and screen screenshot Moire patterns.
    """
    client_ip = get_client_ip(request)
    await rate_limit_check("vision_fraud_check", client_ip, *RateLimitRule.VISION)

    image = await validate_and_read_image(file)

    farm_coords = (farm_lat, farm_lon) if (farm_lat is not None and farm_lon is not None) else None
    loop = asyncio.get_running_loop()
    rep = await loop.run_in_executor(None, _fraud_checker.check_photo, image, farm_coords, None)
    return rep.to_dict()


@router.post("/collect", response_model=PhotoCollectionResponseSchema, status_code=status.HTTP_201_CREATED)
async def collect_training_photo(
    request: Request,
    file: UploadFile = File(..., description="Produce photo contributed by farmer"),
    farmer_id: int = Form(...),
    crop_id: str = Form(..., description="'banana' or 'tomato'"),
    photo_type: str = Form(..., description="'whole_lot', 'close_up', or 'opened_crate'"),
    consent_given: bool = Form(..., description="Statutory DPDP Act consent acknowledgment"),
    consent_language: str = Form("te", description="'en', 'te', 'hi', or 'gu'"),
    device_model: str = Form("Unknown Mobile"),
    lighting_condition: str = Form("diffused_shade"),
    listing_id: int | None = Form(None),
) -> dict[str, Any]:
    """
    Saves consented training photo to collection storage and updates the Label Studio annotation queue.
    Requires explicit DPDP statutory consent.
    """
    client_ip = get_client_ip(request)
    await rate_limit_check("vision_collect", client_ip, *RateLimitRule.VISION)

    if not consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="DPDP statutory consent is mandatory prior to uploading training photos.",
        )

    image = await validate_and_read_image(file)

    try:
        loop = asyncio.get_running_loop()
        record = await loop.run_in_executor(
            None,
            _data_collector.register_photo,
            image,
            farmer_id,
            crop_id,
            photo_type,
            consent_given,
            consent_language,
            device_model,
            lighting_condition,
            listing_id,
        )
        return {
            "status": "success",
            "photo_id": record.photo_id,
            "farmer_id": record.farmer_id,
            "crop_id": record.crop_id,
            "photo_type": record.photo_type,
            "file_path": record.file_path,
            "message": "Photo securely registered and queued for Label Studio agronomist review.",
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register photo: {exc}",
        ) from exc
