"""
Listing Freshness and Media Validation Service.
Enforces:
1. In-app capture within 24 hours (rejecting stale gallery uploads).
2. Fixed 3-photo checklist: whole_lot, close_up, opened_crate.
3. Harvest date validity.
4. Grade compliance (A, B, C).
"""

from datetime import UTC, date, datetime

from backend.app.models.listing import GRADE_DESCRIPTIONS, REQUIRED_PHOTO_CHECKLIST


class MediaValidationError(ValueError):
    """Raised when media or metadata fails authenticity rules."""


class ListingValidator:
    """
    Validates produce listing authenticity before persisting to the database.
    """

    @classmethod
    def validate_listing_payload(
        cls,
        media_checklist: dict[str, str],
        media_captured_at: datetime,
        harvest_date: date,
        grade: str,
        expected_price_kg: float,
        quantity_kg: float,
        now: datetime | None = None,
    ) -> None:
        current_time = now or datetime.now(UTC)

        # 1. Checklist validation: all 3 photos required
        for required_key in REQUIRED_PHOTO_CHECKLIST:
            val = media_checklist.get(required_key)
            if not val or not str(val).strip():
                raise MediaValidationError(
                    f"Fixed photo checklist incomplete: Missing required photo for '{required_key}'. "
                    f"Checklist requires: {REQUIRED_PHOTO_CHECKLIST}"
                )

        # 2. Freshness check: Reject gallery files older than 24 hours
        # Normalize timezone if naive
        capture_time = media_captured_at
        if capture_time.tzinfo is None:
            capture_time = capture_time.replace(tzinfo=UTC)

        age_delta = current_time - capture_time
        if age_delta.total_seconds() > 86400:  # 24 hours
            raise MediaValidationError(
                f"Media freshness check failed: Photo was captured {age_delta.total_seconds() / 3600:.1f} hours ago "
                "(older than 24 hours). Fresh in-app camera capture is strictly required to verify produce freshness."
            )

        if age_delta.total_seconds() < -300:  # Future timestamp tolerance: 5 mins max
            raise MediaValidationError(
                "Media capture timestamp is in the future. Please check camera clock."
            )

        # 3. Harvest date check: within reasonable freshness window (-7 to +7 days)
        today = current_time.date()
        if (today - harvest_date).days > 7:
            raise MediaValidationError(
                f"Harvest date {harvest_date} is older than 7 days. GrowCircle only connects fresh produce."
            )
        if (harvest_date - today).days > 14:
            raise MediaValidationError(
                f"Harvest date {harvest_date} is too far in the future (>14 days). Please list closer to harvest."
            )

        # 4. Grade validation
        clean_grade = grade.upper().strip()
        if clean_grade not in GRADE_DESCRIPTIONS:
            raise MediaValidationError(
                f"Invalid produce grade '{grade}'. Allowed grades: {list(GRADE_DESCRIPTIONS.keys())}"
            )

        # 5. Quantity and Price bounds
        if quantity_kg <= 0:
            raise MediaValidationError("Quantity must be greater than zero kg.")
        if expected_price_kg <= 0:
            raise MediaValidationError("Expected price must be positive.")
