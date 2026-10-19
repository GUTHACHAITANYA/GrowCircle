"""
GrowCircle Great Expectations Compatible Data Validation Suite (Phase ML-0).
Validates cleaned APMC mandi datasets against formal data expectations:
- Schema completeness & null checks
- Domain range bounds & non-negativity
- Compound primary key uniqueness
- Price hierarchy integrity
- Outlier traceability
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class ExpectationSuite:
    """Formal data expectation runner (Great Expectations equivalent)."""

    def __init__(self, name: str = "apmc_cleaned_mandi_prices_suite") -> None:
        self.name = name
        self.results: list[dict[str, Any]] = []

    def run(self, df: pd.DataFrame) -> dict[str, Any]:
        """Runs all registered expectations on the given DataFrame."""
        self.results.clear()

        # 1. Column presence
        required_cols = [
            "mandi_id",
            "crop_id",
            "variety",
            "grade",
            "price_date",
            "min_price_kg",
            "max_price_kg",
            "modal_price_kg",
            "arrival_tonnes",
            "is_outlier",
            "outlier_reason",
        ]
        self._expect_columns_to_exist(df, required_cols)

        # 2. Non-null expectations
        self._expect_column_not_null(df, "mandi_id")
        self._expect_column_not_null(df, "crop_id")
        self._expect_column_not_null(df, "price_date")
        self._expect_column_not_null(df, "modal_price_kg")
        self._expect_column_not_null(df, "min_price_kg")
        self._expect_column_not_null(df, "max_price_kg")

        # 3. Permitted value sets
        self._expect_column_values_in_set(df, "crop_id", {"banana", "tomato", "onion", "potato"})
        self._expect_column_values_in_set(df, "grade", {"FAQ", "A", "B", "C", "SUPER"})

        # 4. Range bounds
        clean_df = df[~df["is_outlier"]]
        self._expect_column_values_between(clean_df, "modal_price_kg", min_val=0.5, max_val=250.0, label="clean_rows_modal_price")
        self._expect_column_values_between(df, "modal_price_kg", min_val=0.5, max_val=1500.0, label="all_rows_modal_price")
        self._expect_column_values_between(df, "arrival_tonnes", min_val=0.0, max_val=5000.0)

        # 5. Compound key uniqueness (no duplicates)
        self._expect_compound_unique(df, ["mandi_id", "crop_id", "price_date", "variety", "grade"])

        # 6. Price hierarchy integrity for non-outliers
        self._expect_price_hierarchy_clean_rows(df)

        # 7. Outlier tag integrity
        self._expect_outlier_integrity(df)

        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        success_rate = round((passed / total * 100.0) if total > 0 else 0.0, 2)

        summary = {
            "suite_name": self.name,
            "total_expectations": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate_pct": success_rate,
            "overall_success": passed == total,
            "details": self.results,
        }
        return summary

    def _expect_columns_to_exist(self, df: pd.DataFrame, columns: list[str]) -> None:
        missing = [c for c in columns if c not in df.columns]
        self.results.append({
            "expectation": "expect_table_columns_to_match_set",
            "kwargs": {"columns": columns},
            "success": len(missing) == 0,
            "result": {"missing_columns": missing},
        })

    def _expect_column_not_null(self, df: pd.DataFrame, column: str) -> None:
        null_count = int(df[column].isna().sum()) if column in df.columns else len(df)
        self.results.append({
            "expectation": "expect_column_values_to_not_be_null",
            "kwargs": {"column": column},
            "success": null_count == 0,
            "result": {"null_count": null_count, "total_rows": len(df)},
        })

    def _expect_column_values_in_set(self, df: pd.DataFrame, column: str, allowed_set: set[str]) -> None:
        if column not in df.columns:
            self.results.append({"expectation": "expect_column_values_to_be_in_set", "success": False, "kwargs": {"column": column}})
            return
        actual_set = set(df[column].unique())
        unexpected = actual_set - allowed_set
        self.results.append({
            "expectation": "expect_column_values_to_be_in_set",
            "kwargs": {"column": column, "allowed_set": list(allowed_set)},
            "success": len(unexpected) == 0,
            "result": {"unexpected_values": list(unexpected)},
        })

    def _expect_column_values_between(
        self, df: pd.DataFrame, column: str, min_val: float, max_val: float, label: str | None = None
    ) -> None:
        exp_name = f"expect_column_values_to_be_between_{label}" if label else "expect_column_values_to_be_between"
        if column not in df.columns:
            self.results.append({"expectation": exp_name, "success": False, "kwargs": {"column": column}})
            return
        out_of_bounds = df[(df[column] < min_val) | (df[column] > max_val)]
        self.results.append({
            "expectation": exp_name,
            "kwargs": {"column": column, "min_value": min_val, "max_value": max_val, "label": label},
            "success": len(out_of_bounds) == 0,
            "result": {"out_of_bounds_count": len(out_of_bounds)},
        })

    def _expect_compound_unique(self, df: pd.DataFrame, columns: list[str]) -> None:
        duplicates = int(df.duplicated(subset=columns).sum())
        self.results.append({
            "expectation": "expect_compound_columns_to_be_unique",
            "kwargs": {"columns": columns},
            "success": duplicates == 0,
            "result": {"duplicate_count": duplicates},
        })

    def _expect_price_hierarchy_clean_rows(self, df: pd.DataFrame) -> None:
        clean_df = df[~df["is_outlier"]]
        violations = clean_df[
            (clean_df["min_price_kg"] > clean_df["max_price_kg"])
            | (clean_df["modal_price_kg"] < clean_df["min_price_kg"])
            | (clean_df["modal_price_kg"] > clean_df["max_price_kg"])
        ]
        self.results.append({
            "expectation": "expect_price_hierarchy_for_non_outliers",
            "kwargs": {"rule": "min_price <= modal_price <= max_price on clean rows"},
            "success": len(violations) == 0,
            "result": {"violation_count": len(violations), "clean_rows_checked": len(clean_df)},
        })

    def _expect_outlier_integrity(self, df: pd.DataFrame) -> None:
        outliers = df[df["is_outlier"]]
        missing_reasons = outliers[outliers["outlier_reason"].str.strip().isin(["", "clean"])]
        self.results.append({
            "expectation": "expect_outlier_flag_integrity",
            "kwargs": {"rule": "Every flagged outlier has non-empty reason"},
            "success": len(missing_reasons) == 0,
            "result": {"outliers_count": len(outliers), "unspecified_reason_count": len(missing_reasons)},
        })


def validate_processed_dataset(csv_path: str = "data/processed/cleaned_mandi_prices.csv") -> dict[str, Any]:
    """Validates the processed dataset and returns expectation report."""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Processed dataset not found at {csv_path}")
    df = pd.read_csv(path)
    suite = ExpectationSuite()
    report = suite.run(df)
    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    rep = validate_processed_dataset()
    print(f"Expectation Suite Run: {rep['passed']} / {rep['total_expectations']} passed ({rep['success_rate_pct']}%)")
    print("Overall Success:", rep["overall_success"])
    if not rep["overall_success"]:
        print(json.dumps([r for r in rep["details"] if not r["success"]], indent=2))
