"""
Comprehensive Unit and Integration Tests for Anomaly Detection (Phase ML-2).
Verifies:
1. Deterministic Rule Layer (Negative, Inverted, Modal OOB, Unit Errors, 10x Jumps).
2. Statistical Residual Robust Z-Score & Isolation Forest.
3. Auto-Clearing Heuristics (Spatial neighbor & supply shock corroboration).
4. Reporting Drop & Source Outage Detector.
5. Deal & Marketplace Integrity (Lowballs, Cancellations, Photo Reuse).
"""

from __future__ import annotations

from datetime import date

from ml.anomaly.deal_anomalies import deal_anomaly_detector
from ml.anomaly.price_anomalies import price_anomaly_detector
from ml.anomaly.reporting_drops import reporting_drop_detector


# -------------------------------------------------------------------------
# 1. Price Anomaly Rule Layer Tests
# -------------------------------------------------------------------------
def test_rule_layer_negative_and_zero_prices() -> None:
    res_neg = price_anomaly_detector.evaluate_price({
        "crop_id": "banana",
        "mandi_id": "ap-guntur-01",
        "min_price_kg": -5.0,
        "max_price_kg": 25.0,
        "modal_price_kg": 20.0,
    })
    assert res_neg.is_anomaly is True
    assert res_neg.reason_code == "RULE_NEGATIVE_OR_ZERO"
    assert res_neg.severity == "CRITICAL"
    assert res_neg.is_auto_cleared is False

    res_zero = price_anomaly_detector.evaluate_price({
        "crop_id": "banana",
        "mandi_id": "ap-guntur-01",
        "min_price_kg": 0.0,
        "max_price_kg": 0.0,
        "modal_price_kg": 0.0,
    })
    assert res_zero.is_anomaly is True
    assert res_zero.reason_code == "RULE_NEGATIVE_OR_ZERO"


def test_rule_layer_inverted_bounds() -> None:
    res = price_anomaly_detector.evaluate_price({
        "crop_id": "tomato",
        "mandi_id": "ap-madanapalle-01",
        "min_price_kg": 35.0,
        "max_price_kg": 20.0,
        "modal_price_kg": 25.0,
    })
    assert res.is_anomaly is True
    assert res.reason_code == "RULE_INVERTED_RANGE"
    assert res.severity == "CRITICAL"


def test_rule_layer_modal_out_of_bounds() -> None:
    res = price_anomaly_detector.evaluate_price({
        "crop_id": "onion",
        "mandi_id": "ap-kurnool-01",
        "min_price_kg": 20.0,
        "max_price_kg": 30.0,
        "modal_price_kg": 35.0,  # exceeds max
    })
    assert res.is_anomaly is True
    assert res.reason_code == "RULE_MODAL_OUT_OF_BOUNDS"
    assert res.severity == "HIGH"


def test_rule_layer_unit_error_detection() -> None:
    # Agmarknet raw quintal entered directly into kg field (e.g. 3500 instead of 35)
    res = price_anomaly_detector.evaluate_price({
        "crop_id": "banana",
        "mandi_id": "ap-guntur-01",
        "min_price_kg": 3000.0,
        "max_price_kg": 4000.0,
        "modal_price_kg": 3500.0,
    })
    assert res.is_anomaly is True
    assert res.reason_code == "RULE_UNIT_ERROR"
    assert res.severity == "CRITICAL"
    assert res.is_auto_cleared is False


def test_rule_layer_10x_vertical_jump() -> None:
    # Banana normal modal ~25. 260 is a 10x typographical jump
    res = price_anomaly_detector.evaluate_price(
        {
            "crop_id": "banana",
            "mandi_id": "ap-guntur-01",
            "min_price_kg": 240.0,
            "max_price_kg": 280.0,
            "modal_price_kg": 260.0,
            "price_date": date(2026, 10, 1),
        },
        as_of=date(2026, 10, 1),
    )
    assert res.is_anomaly is True
    assert res.reason_code == "RULE_10X_SPIKE"
    assert res.severity == "CRITICAL"


# -------------------------------------------------------------------------
# 2. Statistical Layer & Auto-Clearing Tests
# -------------------------------------------------------------------------
def test_statistical_residual_anomaly_uncorroborated_requires_admin() -> None:
    # Moderate price spike without neighbor corroboration or arrival surge
    res = price_anomaly_detector.evaluate_price(
        {
            "crop_id": "potato",
            "mandi_id": "ap-kurnool-01",
            "min_price_kg": 40.0,
            "max_price_kg": 50.0,
            "modal_price_kg": 46.0,  # normal ~20, Z > 4.5
            "arrival_tonnes": 30.0,  # ordinary arrivals
            "price_date": date(2026, 12, 1),
        },
        as_of=date(2026, 12, 1),
    )
    assert res.is_anomaly is True
    assert res.reason_code in ["STAT_RESIDUAL_ZSCORE", "STAT_ISOLATION_FOREST"]
    assert res.is_auto_cleared is False


def test_auto_clearing_supply_shock_corroboration() -> None:
    # Sharp price drop accompanied by a 4x surge in market arrival tonnes
    res = price_anomaly_detector.evaluate_price(
        {
            "crop_id": "banana",
            "mandi_id": "ap-guntur-01",
            "min_price_kg": 4.0,
            "max_price_kg": 6.0,
            "modal_price_kg": 5.0,  # drop from ~25
            "arrival_tonnes": 350.0,  # massive arrival glut (normal ~15t)
            "price_date": date(2026, 12, 1),
        },
        as_of=date(2026, 12, 1),
    )
    assert res.is_anomaly is True
    assert res.is_auto_cleared is True
    assert "Supply shock" in (res.auto_cleared_reason or "")


# -------------------------------------------------------------------------
# 3. Reporting Drop & Source Outage Detector Tests
# -------------------------------------------------------------------------
def test_reporting_drop_normal_weekday() -> None:
    # Tuesday with 19 reporting mandis (expected ~18.5)
    res = reporting_drop_detector.evaluate_reporting(
        target_date=date(2026, 10, 13),  # Tuesday
        actual_mandis_count=19,
    )
    assert res.status == "HEALTHY"
    assert res.is_outage_alert is False


def test_reporting_drop_normal_sunday() -> None:
    # Sunday with 2 reporting mandis (expected ~2.0)
    res = reporting_drop_detector.evaluate_reporting(
        target_date=date(2026, 10, 11),  # Sunday
        actual_mandis_count=2,
    )
    assert res.status == "NORMAL_WEEKEND"
    assert res.is_outage_alert is False


def test_reporting_drop_severe_outage_alert() -> None:
    # Tuesday with only 2 reporting mandis (massive drop from ~18.5)
    res = reporting_drop_detector.evaluate_reporting(
        target_date=date(2026, 10, 13),  # Tuesday
        actual_mandis_count=2,
    )
    assert res.status == "CRITICAL_OUTAGE"
    assert res.is_outage_alert is True
    assert "CRITICAL SOURCE OUTAGE ALERT" in res.alert_message


# -------------------------------------------------------------------------
# 4. Deal Anomaly Detector Tests
# -------------------------------------------------------------------------
def test_deal_offer_extreme_lowball() -> None:
    # Mandi is ₹25, offer is ₹8 (68% lowball)
    res = deal_anomaly_detector.evaluate_offer_price(
        offered_price_kg=8.0,
        mandi_benchmark_price_kg=25.0,
        crop_id="banana",
    )
    assert res.is_anomaly is True
    assert res.reason_code == "DEAL_OFFER_EXTREME_LOWBALL"
    assert res.severity == "HIGH"


def test_deal_offer_fair_price_passes() -> None:
    # Mandi is ₹25, offer is ₹24 (4% variance)
    res = deal_anomaly_detector.evaluate_offer_price(
        offered_price_kg=24.0,
        mandi_benchmark_price_kg=25.0,
        crop_id="banana",
    )
    assert res.is_anomaly is False
    assert res.reason_code == "CLEAN"


def test_deal_serial_cancellations() -> None:
    # 4 cancellations out of 5 interactions (80% rate)
    res = deal_anomaly_detector.evaluate_user_cancellations(
        user_id=456,
        total_interactions=5,
        cancelled_count=4,
    )
    assert res.is_anomaly is True
    assert res.reason_code == "DEAL_SERIAL_CANCELLATIONS"
    assert res.severity == "HIGH"


def test_deal_suspicious_photo_reuse() -> None:
    # Farmer 101 registers a physical produce photo
    test_hash = "sha256:unique_crate_fingerprint_abc123"
    deal_anomaly_detector.register_listing_photos(
        listing_id=50,
        farmer_id=101,
        photo_hashes=[test_hash],
        created_at=date(2026, 10, 1),
    )

    # Farmer 202 attempts to upload the identical photo hash (stolen image)
    res = deal_anomaly_detector.evaluate_listing_photos(
        current_farmer_id=202,
        photo_hashes=[test_hash],
        as_of=date(2026, 10, 2),
    )
    assert res.is_anomaly is True
    assert res.reason_code == "DEAL_STOLEN_PHOTO_REUSE"
    assert res.severity == "CRITICAL"
