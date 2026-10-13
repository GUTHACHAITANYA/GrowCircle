"""
Unit tests for Agmarknet Data Quality Guard.
Enforces rejection of invalid, negative, out-of-order, or anomalous records.
"""

from backend.app.services.data_quality import DataQualityGuard


def test_valid_record_passes() -> None:
    valid_record = {
        "market": "Guntur",
        "commodity": "Banana",
        "arrival_date": "2026-10-13",
        "min_price": 2200,
        "max_price": 2800,
        "modal_price": 2500,
    }
    is_valid, reason = DataQualityGuard.validate_price_record(valid_record)
    assert is_valid is True
    assert reason is None


def test_missing_required_fields_rejected() -> None:
    bad_record = {
        "market": "Guntur",
        # missing commodity
        "arrival_date": "2026-10-13",
        "modal_price": 2500,
    }
    is_valid, reason = DataQualityGuard.validate_price_record(bad_record)
    assert is_valid is False
    assert "Missing required field" in (reason or "")


def test_negative_or_zero_price_rejected() -> None:
    bad_record = {
        "market": "Guntur",
        "commodity": "Banana",
        "arrival_date": "2026-10-13",
        "min_price": -500,
        "max_price": 2800,
        "modal_price": 2500,
    }
    is_valid, reason = DataQualityGuard.validate_price_record(bad_record)
    assert is_valid is False
    assert "Non-positive price" in (reason or "")


def test_min_greater_than_max_rejected() -> None:
    bad_record = {
        "market": "Guntur",
        "commodity": "Banana",
        "arrival_date": "2026-10-13",
        "min_price": 3000,
        "max_price": 2500,
        "modal_price": 2700,
    }
    is_valid, reason = DataQualityGuard.validate_price_record(bad_record)
    assert is_valid is False
    assert "Inconsistent range" in (reason or "")


def test_modal_outside_min_max_rejected() -> None:
    bad_record = {
        "market": "Guntur",
        "commodity": "Banana",
        "arrival_date": "2026-10-13",
        "min_price": 2000,
        "max_price": 2500,
        "modal_price": 2800,  # exceeds max
    }
    is_valid, reason = DataQualityGuard.validate_price_record(bad_record)
    assert is_valid is False
    assert "outside range" in (reason or "")


def test_10x_spike_anomaly_detected() -> None:
    spike_record = {
        "market": "Guntur",
        "commodity": "Banana",
        "arrival_date": "2026-10-13",
        "min_price": 25000,
        "max_price": 30000,
        "modal_price": 28000,  # 10x higher than normal 2500
    }
    historical_avg = 2500.0
    is_valid, reason = DataQualityGuard.validate_price_record(
        spike_record, historical_modal_quintal=historical_avg
    )
    assert is_valid is False
    assert "10x Price Spike" in (reason or "")


def test_10x_crash_anomaly_detected() -> None:
    crash_record = {
        "market": "Guntur",
        "commodity": "Banana",
        "arrival_date": "2026-10-13",
        "min_price": 100,
        "max_price": 200,
        "modal_price": 150,  # crash compared to 2500
    }
    historical_avg = 2500.0
    is_valid, reason = DataQualityGuard.validate_price_record(
        crash_record, historical_modal_quintal=historical_avg
    )
    assert is_valid is False
    assert "10x Price Crash" in (reason or "")
