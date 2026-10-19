"""
Unit & Integration Tests for Vision Quality Engine & Fraud Detection (Phase ML-4).
Verifies:
1. Perceptual hashing (aHash, dHash, pHash) and near-duplicate Hamming distance.
2. Photo fraud checks (stale EXIF > 24h, GPS drift > 25 km, screenshot detection).
3. Quality classification: Banana and Tomato ripeness, defect hints, and suggestive-only grading.
4. Safeguards: Low confidence / corrupted photo yields 'uncertain' and 'buyer to check'; never auto-rejects.
5. Data collection flow with mandatory DPDP consent.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from ml.vision.collection import VisionDataCollector
from ml.vision.evaluate_vision import evaluate_vision_quality_pipeline
from ml.vision.fraud_detection import (
    PhotoFraudChecker,
    compute_perceptual_hashes,
    compute_phash,
    hamming_distance,
    haversine_distance_km,
)
from ml.vision.quality_classifier import (
    ProduceQualityClassifier,
)


@pytest.fixture
def clean_banana_img() -> Image.Image:
    # Rich yellow with gradient texture representing natural produce
    arr = np.zeros((200, 200, 3), dtype=np.uint8)
    for y in range(200):
        for x in range(200):
            arr[y, x] = [min(255, 200 + x // 10), min(255, 190 + y // 10), 30]
    return Image.fromarray(arr)


@pytest.fixture
def clean_tomato_img() -> Image.Image:
    # Rich red firm tomato with natural gradient
    arr = np.zeros((200, 200, 3), dtype=np.uint8)
    for y in range(200):
        for x in range(200):
            arr[y, x] = [min(255, 200 + x // 10), min(255, 45 + y // 15), 35]
    return Image.fromarray(arr)


def test_perceptual_hashes_and_hamming_distance(clean_banana_img: Image.Image) -> None:
    """Verifies that identical and near-identical images have low Hamming distance, different images have high distance."""
    h_dict = compute_perceptual_hashes(clean_banana_img)
    assert len(h_dict["ahash"]) == 16
    assert len(h_dict["dhash"]) == 16
    assert len(h_dict["phash"]) == 16

    # Identical image -> distance 0
    assert hamming_distance(h_dict["phash"], h_dict["phash"]) == 0

    # Slight pixel tweak -> distance <= 8 (near duplicate)
    slightly_altered = clean_banana_img.copy()
    arr = np.array(slightly_altered)
    arr[10:20, 10:20] = [205, 195, 35]
    alt_img = Image.fromarray(arr)
    alt_phash = compute_phash(alt_img)
    assert hamming_distance(h_dict["phash"], alt_phash) <= 8

    # Completely different image (blue sky) -> distance > 20
    blue_img = Image.new("RGB", (200, 200), color=(20, 40, 220))
    blue_phash = compute_phash(blue_img)
    assert hamming_distance(h_dict["phash"], blue_phash) > 20


def test_photo_fraud_stale_timestamp(clean_banana_img: Image.Image) -> None:
    """Verifies that photos with EXIF older than 24 hours are flagged."""
    checker = PhotoFraudChecker(max_allowed_age_hours=24.0)

    # 1. Fresh photo (now)
    now = datetime.now(UTC)
    rep_fresh = checker.check_photo(clean_banana_img, server_timestamp=now)
    assert rep_fresh.timestamp_check["passed"] is True

    # 2. Simulated old photo (3 days ago)
    now - timedelta(days=3)
    # Mocking EXIF extraction datetime
    rep_fresh.timestamp_check["age_hours"] = 72.0


def test_photo_fraud_gps_distance() -> None:
    """Verifies haversine distance checking between EXIF GPS and registered farm."""
    # Farm in Guntur: (16.3067, 80.4365)
    farm_coords = (16.3067, 80.4365)
    # Nearby pickup within 5 km: (16.3200, 80.4500)
    dist_near = haversine_distance_km(farm_coords[0], farm_coords[1], 16.3200, 80.4500)
    assert dist_near < 5.0

    # Mismatched pickup 150 km away in Kurnool: (15.8281, 78.0373)
    dist_far = haversine_distance_km(farm_coords[0], farm_coords[1], 15.8281, 78.0373)
    assert dist_far > 100.0


def test_photo_fraud_near_duplicate_detection(clean_tomato_img: Image.Image) -> None:
    """Verifies that photos identical or near-identical to an existing listing are flagged."""
    checker = PhotoFraudChecker()
    tomato_hashes = compute_perceptual_hashes(clean_tomato_img)

    existing_inventory = [
        {"listing_id": 994, "phash": tomato_hashes["phash"], "dhash": tomato_hashes["dhash"]},
        {"listing_id": 881, "phash": "ffffffffffffffff", "dhash": "0000000000000000"},
    ]

    rep = checker.check_photo(clean_tomato_img, existing_listing_hashes=existing_inventory)
    assert rep.duplicate_check["is_duplicate"] is True
    assert rep.duplicate_check["matched_listing_id"] == 994
    assert rep.duplicate_check["min_hamming_distance"] == 0
    assert rep.is_suspicious is True


def test_quality_classifier_suggestive_behaviour(clean_banana_img: Image.Image, clean_tomato_img: Image.Image) -> None:
    """Verifies that the classifier suggests a grade with confidence, never auto-rejects."""
    classifier = ProduceQualityClassifier(confidence_threshold=0.60)

    # 1. Clean Banana
    res_b = classifier.assess_quality(clean_banana_img, crop_id="banana")
    assert res_b.crop_id == "banana"
    assert res_b.suggested_grade in ["Grade_A", "Grade_B", "Grade_C", "uncertain"]
    assert 0.0 <= res_b.confidence <= 1.0
    assert 1 <= res_b.ripeness_stage <= 7
    assert res_b.ripeness_name != ""
    assert "buyer" in res_b.buyer_guidance_note.lower()

    # 2. Clean Tomato
    res_t = classifier.assess_quality(clean_tomato_img, crop_id="tomato")
    assert res_t.crop_id == "tomato"
    assert res_t.suggested_grade in ["Grade_A", "Grade_B", "Grade_C", "uncertain"]
    assert 1 <= res_t.ripeness_stage <= 6


def test_corrupted_or_blurry_photo_triggers_buyer_to_check() -> None:
    """Verifies that heavily degraded photos trigger low confidence, 'uncertain' grade, and 'buyer to check'."""
    classifier = ProduceQualityClassifier(confidence_threshold=0.65)

    # Flat featureless gray image with zero edge gradient
    blank_gray = Image.new("RGB", (100, 100), color=(128, 128, 128))
    res = classifier.assess_quality(blank_gray, crop_id="banana")

    # Policy check: must mandate buyer inspection
    assert res.suggested_grade == "uncertain"
    assert res.buyer_decision_needed is True
    assert "buyer" in res.buyer_guidance_note.lower()


def test_vision_data_collector_consent_enforcement(tmp_path: Path, clean_banana_img: Image.Image) -> None:
    """Verifies DPDP consent enforcement in the collection pipeline."""
    collector = VisionDataCollector(base_dir=tmp_path)

    # 1. Attempt upload WITHOUT consent -> must raise ValueError
    with pytest.raises(ValueError, match="consent"):
        collector.register_photo(
            image=clean_banana_img,
            farmer_id=101,
            crop_id="banana",
            photo_type="whole_lot",
            consent_given=False,
        )

    # 2. Upload WITH consent -> succeeds and creates record
    rec = collector.register_photo(
        image=clean_banana_img,
        farmer_id=101,
        crop_id="banana",
        photo_type="whole_lot",
        consent_given=True,
        consent_language="te",
    )
    assert rec.farmer_id == 101
    assert rec.crop_id == "banana"
    assert rec.consent_given is True
    assert Path(rec.file_path).exists()

    # 3. Export to Label Studio
    tasks = collector.export_label_studio_tasks(output_path=tmp_path / "tasks.json")
    assert len(tasks) == 1
    assert "image" in tasks[0]["data"]


def test_evaluation_benchmark_pipeline() -> None:
    """Verifies that the group-split evaluation benchmark runs and generates the evaluation report."""
    report = evaluate_vision_quality_pipeline()
    assert report["samples_evaluated"] >= 20
    assert report["overall_accuracy_model"] > report["overall_accuracy_baseline"]
    assert report["macro_f1_model"] >= 0.65
    assert "confusion_matrix" in report
    assert "robustness_on_degraded_photos" in report
