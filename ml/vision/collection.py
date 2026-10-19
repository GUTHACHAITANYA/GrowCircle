"""
Produce Quality Photo Collection & Label Studio Pipeline (Phase ML-4).
Manages:
1. DPDP Act 2023 multilingual consent verification.
2. 3-Photo Checklist validation (whole_lot, close_up, opened_crate).
3. Metadata cataloging (device variety, lighting conditions, angles).
4. Label Studio annotation queue preparation.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image

from ml.vision.fraud_detection import compute_perceptual_hashes

COLLECTION_DIR = Path("data/vision_collection")
IMAGES_DIR = COLLECTION_DIR / "images"
MANIFEST_PATH = COLLECTION_DIR / "collection_manifest.json"
LABEL_STUDIO_EXPORT_PATH = COLLECTION_DIR / "label_studio_tasks.json"

CONSENT_STRINGS = {
    "en": "I consent to GrowCircle analyzing photos of my produce to suggest quality grades and train quality models.",
    "te": "నా పంట నాణ్యత గ్రేడ్‌లను అంచనా వేయడానికి నా ఫోటోలను విశ్లేషించడానికి గ్రోసర్కిల్‌కు అనుమతి ఇస్తున్నాను.",
    "hi": "मैं ग्रोसर्कल को मेरी फसल के फोटो का विश्लेषण करने की सहमति देता हूँ।",
    "gu": "હું ગ્રોસર્કલને મારા પાકના ફોટાનું વિશ્લેષણ કરવાની મંજૂરી આપું છું.",
}


@dataclass
class CollectedPhotoRecord:
    photo_id: str
    farmer_id: int
    listing_id: int | None
    crop_id: str
    photo_type: str  # 'whole_lot', 'close_up', 'opened_crate'
    device_model: str
    lighting_condition: str  # 'harsh_sunlight', 'diffused_shade', 'indoor_shed'
    consent_given: bool
    consent_language: str
    file_path: str
    file_size_bytes: int
    resolution: tuple[int, int]
    perceptual_hashes: dict[str, str]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class VisionDataCollector:
    """
    Manages safe intake of produce photos and prepares Label Studio annotation tasks.
    """

    def __init__(self, base_dir: Path = COLLECTION_DIR) -> None:
        self.base_dir = base_dir
        self.images_dir = base_dir / "images"
        self.manifest_path = base_dir / "collection_manifest.json"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.records: list[CollectedPhotoRecord] = self._load_manifest()

    def _load_manifest(self) -> list[CollectedPhotoRecord]:
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, encoding="utf-8") as f:
                    data = json.load(f)
                    return [CollectedPhotoRecord(**item) for item in data]
            except Exception:
                return []
        return []

    def _save_manifest(self) -> None:
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in self.records], f, indent=2)

    def register_photo(
        self,
        image: Image.Image,
        farmer_id: int,
        crop_id: str,
        photo_type: str,
        consent_given: bool,
        consent_language: str = "te",
        device_model: str = "Unknown Mobile",
        lighting_condition: str = "diffused_shade",
        listing_id: int | None = None,
    ) -> CollectedPhotoRecord:
        """
        Validates DPDP consent, stores photo safely, and logs collection metadata.
        """
        if not consent_given:
            raise ValueError("DPDP statutory consent is mandatory prior to uploading training photos.")

        valid_types = {"whole_lot", "close_up", "opened_crate"}
        if photo_type not in valid_types:
            raise ValueError(f"Invalid photo_type '{photo_type}'. Must be one of {valid_types}.")

        crop = crop_id.lower().strip()
        timestamp_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        photo_id = f"{crop}_{farmer_id}_{photo_type}_{timestamp_str}"
        target_path = self.images_dir / f"{photo_id}.jpg"

        # Save optimized JPEG
        image.convert("RGB").save(target_path, "JPEG", quality=90)
        file_size = target_path.stat().st_size
        hashes = compute_perceptual_hashes(image)

        record = CollectedPhotoRecord(
            photo_id=photo_id,
            farmer_id=farmer_id,
            listing_id=listing_id,
            crop_id=crop,
            photo_type=photo_type,
            device_model=device_model,
            lighting_condition=lighting_condition,
            consent_given=consent_given,
            consent_language=consent_language,
            file_path=str(target_path),
            file_size_bytes=file_size,
            resolution=image.size,
            perceptual_hashes=hashes,
            created_at=datetime.now(UTC).isoformat(),
        )

        self.records.append(record)
        self._save_manifest()
        return record

    def export_label_studio_tasks(self, output_path: Path = LABEL_STUDIO_EXPORT_PATH) -> list[dict[str, Any]]:
        """
        Generates Label Studio task JSON matching the XML schema in vision_data_plan.md.
        """
        tasks: list[dict[str, Any]] = []
        for r in self.records:
            task = {
                "data": {
                    "image": f"/data/local-files/?d={Path(r.file_path).name}",
                    "crop_id": r.crop_id,
                    "photo_type": r.photo_type,
                    "farmer_id": r.farmer_id,
                    "lighting": r.lighting_condition,
                    "device": r.device_model,
                },
                "meta": {
                    "photo_id": r.photo_id,
                    "created_at": r.created_at,
                },
            }
            tasks.append(task)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2)

        return tasks

    def get_collection_statistics(self) -> dict[str, Any]:
        """Returns statistics on dataset scale, crop split, and 3-photo checklist completeness."""
        total = len(self.records)
        by_crop: dict[str, int] = {}
        by_type: dict[str, int] = {}
        by_lighting: dict[str, int] = {}

        for r in self.records:
            by_crop[r.crop_id] = by_crop.get(r.crop_id, 0) + 1
            by_type[r.photo_type] = by_type.get(r.photo_type, 0) + 1
            by_lighting[r.lighting_condition] = by_lighting.get(r.lighting_condition, 0) + 1

        return {
            "total_photos_collected": total,
            "by_crop": by_crop,
            "by_photo_type": by_type,
            "by_lighting_condition": by_lighting,
            "minimum_recommended_samples": 700,
            "readiness_for_deep_training": total >= 700,
        }
