"""
Unit tests for agricultural price unit conversions.
1 Quintal = 100 Kilograms.
1 Metric Ton = 10 Quintals = 1,000 Kilograms.
"""

import pytest

from backend.app.services.data_quality import quintal_to_kg, quintal_to_ton


def test_quintal_to_kg_conversion() -> None:
    # 2500 / quintal = 25.0 / kg
    assert quintal_to_kg(2500.0) == 25.0
    # 1850 / quintal = 18.5 / kg
    assert quintal_to_kg(1850.0) == 18.5
    # 2435 / quintal = 24.35 / kg
    assert quintal_to_kg(2435.0) == 24.35
    # 0 / quintal = 0.0 / kg
    assert quintal_to_kg(0.0) == 0.0


def test_quintal_to_ton_conversion() -> None:
    # 2500 / quintal = 25,000 / ton
    assert quintal_to_ton(2500.0) == 25000.0
    # 1850 / quintal = 18,500 / ton
    assert quintal_to_ton(1850.0) == 18500.0


def test_negative_price_raises_error() -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        quintal_to_kg(-500.0)

    with pytest.raises(ValueError, match="cannot be negative"):
        quintal_to_ton(-100.0)
