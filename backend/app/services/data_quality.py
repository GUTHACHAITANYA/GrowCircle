"""
Data Quality Guard and unit conversion functions for Agmarknet mandi data.
Enforces non-negotiable rules:
- 1 Quintal = 100 kg, 1 Ton = 1000 kg (10 Quintals)
- Anomaly detection: negative values, min > max, min > modal or modal > max, 10x jumps/crashes.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def quintal_to_kg(price_per_quintal: float) -> float:
    """
    Converts price per quintal (100 kg) to price per kilogram.
    Formula: Price_kg = Price_quintal / 100
    """
    if price_per_quintal < 0:
        raise ValueError("Price per quintal cannot be negative")
    return round(price_per_quintal / 100.0, 2)


def quintal_to_ton(price_per_quintal: float) -> float:
    """
    Converts price per quintal to price per metric ton (1000 kg / 10 quintals).
    Formula: Price_ton = Price_quintal * 10
    """
    if price_per_quintal < 0:
        raise ValueError("Price per quintal cannot be negative")
    return round(price_per_quintal * 10.0, 2)


class DataQualityGuard:
    """
    Inspects incoming Agmarknet commodity records and flags or rejects anomalies.
    """

    @staticmethod
    def validate_price_record(
        record: dict[str, Any],
        historical_modal_quintal: float | None = None,
    ) -> tuple[bool, str | None]:
        """
        Validates an incoming mandi price record.
        Returns:
            (is_valid: bool, error_reason: str | None)
        """
        # 1. Required fields presence
        required_keys = ["market", "commodity", "arrival_date", "modal_price"]
        for key in required_keys:
            if key not in record or record[key] is None or str(record[key]).strip() == "":
                return False, f"Missing required field: '{key}'"

        # 2. Parse numeric prices
        try:
            min_price = float(record.get("min_price", record["modal_price"]))
            max_price = float(record.get("max_price", record["modal_price"]))
            modal_price = float(record["modal_price"])
        except (ValueError, TypeError) as exc:
            return False, f"Invalid non-numeric price value: {exc}"

        # 3. Check for non-positive or negative prices
        if min_price <= 0 or max_price <= 0 or modal_price <= 0:
            return (
                False,
                f"Non-positive price found (min={min_price}, max={max_price}, modal={modal_price})",
            )

        # 4. Check ordering: min_price <= modal_price <= max_price
        if min_price > max_price:
            return False, f"Inconsistent range: min_price ({min_price}) > max_price ({max_price})"

        if modal_price < min_price or modal_price > max_price:
            return False, f"Modal price ({modal_price}) outside range [{min_price}, {max_price}]"

        # 5. Sanity bounds: 1 quintal is between ₹50 and ₹200,000 (0.50/kg to 2000/kg)
        if modal_price < 50.0 or modal_price > 200_000.0:
            return (
                False,
                f"Modal price ({modal_price}) exceeds agricultural plausibility bounds [50, 200000]",
            )

        # 6. Anomaly Spike/Crash Check (10x jump relative to recent 7-day average)
        if historical_modal_quintal is not None and historical_modal_quintal > 0:
            upper_spike_limit = historical_modal_quintal * 10.0
            lower_crash_limit = historical_modal_quintal / 10.0

            if modal_price > upper_spike_limit:
                return (
                    False,
                    f"10x Price Spike detected: modal={modal_price} vs historical_avg={historical_modal_quintal}",
                )

            if modal_price < lower_crash_limit:
                return (
                    False,
                    f"10x Price Crash detected: modal={modal_price} vs historical_avg={historical_modal_quintal}",
                )

        return True, None
