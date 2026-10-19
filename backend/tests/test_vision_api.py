"""
FastAPI Integration Tests for Vision Endpoints (Phase ML-4).
Verifies:
1. POST /vision/inspect (suggestive grading, confidence, latency, policy notice).
2. POST /vision/fraud-check (perceptual hashes, EXIF, screenshot checks).
3. POST /vision/collect (DPDP consent mandatory, 400 on refusal, 201 on acceptance).
"""

from __future__ import annotations

import io

import pytest
from httpx import AsyncClient
from PIL import Image


def create_test_image_bytes(color: tuple[int, int, int] = (210, 200, 30)) -> bytes:
    img = Image.new("RGB", (128, 128), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_vision_inspect_endpoint(client: AsyncClient) -> None:
    """Verifies POST /vision/inspect returns suggestive grading, confidence, and fraud checks."""
    img_bytes = create_test_image_bytes(color=(210, 200, 30))
    files = {"file": ("banana_test.jpg", img_bytes, "image/jpeg")}
    data = {
        "crop_id": "banana",
        "listing_id": "101",
        "farm_lat": "16.3067",
        "farm_lon": "80.4365",
    }

    res = await client.post("/vision/inspect", files=files, data=data)
    assert res.status_code == 200
    res_data = res.json()

    assert res_data["crop_id"] == "banana"
    assert res_data["suggested_grade"] in ["Grade_A", "Grade_B", "Grade_C", "uncertain"]
    assert 0.0 <= res_data["confidence"] <= 1.0
    assert 1 <= res_data["ripeness_stage"] <= 7
    assert res_data["ripeness_name"] != ""
    assert res_data["fallback_triggered"] is False
    assert res_data["latency_ms"] >= 0.0

    # Policy Notice verification
    assert "never auto-rejected" in res_data["policy_notice"].lower()

    # Fraud Report verification
    fraud = res_data["fraud_report"]
    assert "fraud_risk_score" in fraud
    assert fraud["recommendation"] in ["PASS", "BUYER_VERIFY", "FLAGGED_SUSPICIOUS"]
    assert "perceptual_hashes" in fraud
    assert "phash" in fraud["perceptual_hashes"]


@pytest.mark.asyncio
async def test_vision_fraud_check_endpoint(client: AsyncClient) -> None:
    """Verifies POST /vision/fraud-check evaluates photo integrity."""
    img_bytes = create_test_image_bytes(color=(200, 50, 40))
    files = {"file": ("tomato_fraud_test.jpg", img_bytes, "image/jpeg")}
    data = {"farm_lat": "16.3067", "farm_lon": "80.4365"}

    res = await client.post("/vision/fraud-check", files=files, data=data)
    assert res.status_code == 200
    res_data = res.json()

    assert "fraud_risk_score" in res_data
    assert "recommendation" in res_data
    assert res_data["duplicate_check"]["is_duplicate"] is False
    assert len(res_data["perceptual_hashes"]["dhash"]) == 16


@pytest.mark.asyncio
async def test_vision_collect_endpoint_consent_enforcement(client: AsyncClient) -> None:
    """Verifies DPDP consent enforcement in POST /vision/collect."""
    img_bytes = create_test_image_bytes()

    # 1. Missing consent -> 400 Bad Request
    files_no_consent = {"file": ("training_sample.jpg", img_bytes, "image/jpeg")}
    data_no_consent = {
        "farmer_id": "42",
        "crop_id": "banana",
        "photo_type": "whole_lot",
        "consent_given": "false",
        "consent_language": "te",
    }
    res_fail = await client.post("/vision/collect", files=files_no_consent, data=data_no_consent)
    assert res_fail.status_code == 400
    assert "consent" in res_fail.json()["detail"].lower()

    # 2. Valid consent -> 201 Created
    files_consent = {"file": ("training_sample.jpg", img_bytes, "image/jpeg")}
    data_consent = {
        "farmer_id": "42",
        "crop_id": "banana",
        "photo_type": "whole_lot",
        "consent_given": "true",
        "consent_language": "te",
        "device_model": "Redmi Note 11",
        "lighting_condition": "diffused_shade",
    }
    res_ok = await client.post("/vision/collect", files=files_consent, data=data_consent)
    assert res_ok.status_code == 201
    res_ok_data = res_ok.json()
    assert res_ok_data["status"] == "success"
    assert "photo_id" in res_ok_data
    assert res_ok_data["farmer_id"] == 42
    assert "Label Studio" in res_ok_data["message"]
