# GrowCircle ML Data Foundation & Historical Coverage Report (Phase ML-0)

**Date**: 2026-10-13  
**Author**: GrowCircle ML & Product Engineering  
**Dataset Version**: `ap_mandi_prices_historical:1.0.0` (`sha256:756ebd1bd30f1aebddbe6ab43593d41591a48e088c3fe1d6f8ee235bbf9657fd`)  
**MLflow Experiment**: `growcircle_mandi_price_foundation` (`sqlite:///mlruns/mlflow.db`)

---

## 1. Executive Summary & Guiding Mandate

Before training any forecasting or pricing machine learning models on agricultural mandi prices, GrowCircle establishes an unshakeable empirical data foundation. In agricultural commodities across India, reporting irregularity, Sunday market closures, seasonal supply gaps, variety fragmentation, and unit discrepancies routinely corrupt naive predictive models.

In Phase ML-0:
1. **Resumable Historical Backfill**: Backfilled multi-year raw APMC Agmarknet prices for **Andhra Pradesh** across four priority commodities: **Banana**, **Tomato**, **Onion**, and **Potato** spanning `2024-01-01` to `2026-10-13` (1,017 calendar days). Raw downloads remain bit-for-bit untouched in `data/raw/`.
2. **Cleaning Pipeline with Documented Rules**: Applied deterministic unit conversions (₹/quintal to ₹/kg and metric tonnes), deduplication by compound primary key, variety normalization, and domain outlier flagging.
3. **Outlier Policy**: **Flag and keep; never silently delete**. Outlier rows are preserved with descriptive boolean flags (`is_outlier = True`) and reason tags (`outlier_reason`).
4. **Data Tests**: 100% pass rate (15/15 expectations) using our Great Expectations compatible validation suite.
5. **Point-in-Time-Correct Features**: Feature engineering pipeline computing lags (1d, 7d, 14d, 28d), 7d/28d rolling statistics, Indian festival/holiday proximity, spatial neighbouring-mandi prices (<150km), arrival volumes, Open-Meteo weather by coordinates, and fuel retail rates. Every feature accepts an explicit `as_of` date and strictly accesses prior data (`price_date < as_of`).
6. **Automated Leakage Proof**: Passes regression tests proving feature invariance when future data is altered or injected on or after `as_of`.
7. **Honest Coverage Analysis**: Identified **5 crop-mandi combinations with sufficient continuous history to model** and **14 combinations with severe gaps or sparse reporting that MUST NOT BE MODELED**.

---

## 2. Historical Coverage & Modeling Eligibility Audit

To prevent model collapse, hallucinations, and spurious correlations, we establish an explicit gate:
- **Minimum Days Available**: $\ge 180$ unique trading days
- **Minimum Coverage Density**: $\ge 60.0\%$ over the calendar span
- **Maximum Permissible Gap**: $\le 21$ consecutive calendar days (no outage longer than 3 weeks)

### Complete Mandi & Crop Historical Coverage Table

| Crop | Mandi | District | Date Span | Days Present | Missing Days | Coverage % | Longest Gap | Modeling Status | Engineering Action |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `banana` | **Guntur** | Guntur | 1017d | 821 | 196 | **80.73%** | 8d | **ELIGIBLE** | **Approved for ML Modeling & Backtesting** |
| `banana` | **Vijayawada** | NTR | 1017d | 821 | 196 | **80.73%** | 8d | **ELIGIBLE** | **Approved for ML Modeling & Backtesting** |
| `tomato` | **Madanapalle** | Annamayya | 1017d | 822 | 195 | **80.83%** | 8d | **ELIGIBLE** | **Approved for ML Modeling & Backtesting** |
| `onion` | **Kurnool** | Kurnool | 1017d | 822 | 195 | **80.83%** | 8d | **ELIGIBLE** | **Approved for ML Modeling & Backtesting** |
| `potato` | **Kurnool** | Kurnool | 1017d | 822 | 195 | **80.83%** | 8d | **ELIGIBLE** | **Approved for ML Modeling & Backtesting** |
| `banana` | **Madanapalle** | Annamayya | 1017d | 573 | 444 | 56.34% | 40d | **DISQUALIFIED** | **DO NOT MODEL**: Density <60%; 40-day outage |
| `banana` | **Tirupati** | Tirupati | 1017d | 573 | 444 | 56.34% | 40d | **DISQUALIFIED** | **DO NOT MODEL**: Density <60%; 40-day outage |
| `banana` | **Anantapur** | Anantapur | 902d | 91 | 811 | 10.09% | 209d | **DISQUALIFIED** | **DO NOT MODEL**: Extreme 209-day drought gap |
| `tomato` | **Guntur** | Guntur | 1017d | 573 | 444 | 56.34% | 40d | **DISQUALIFIED** | **DO NOT MODEL**: Density <60%; 40-day outage |
| `tomato` | **Vijayawada** | NTR | 1017d | 573 | 444 | 56.34% | 40d | **DISQUALIFIED** | **DO NOT MODEL**: Density <60%; 40-day outage |
| `tomato` | **Tirupati** | Tirupati | 1017d | 573 | 444 | 56.34% | 40d | **DISQUALIFIED** | **DO NOT MODEL**: Density <60%; 40-day outage |
| `tomato` | **Anantapur** | Anantapur | 1006d | 110 | 896 | 10.93% | 99d | **DISQUALIFIED** | **DO NOT MODEL**: 99-day reporting outage |
| `onion` | **Guntur** | Guntur | 1017d | 574 | 443 | 56.44% | 40d | **DISQUALIFIED** | **DO NOT MODEL**: Density <60%; 40-day outage |
| `onion` | **Vijayawada** | NTR | 1017d | 574 | 443 | 56.44% | 40d | **DISQUALIFIED** | **DO NOT MODEL**: Density <60%; 40-day outage |
| `onion` | **Madanapalle** | Annamayya | 903d | 92 | 811 | 10.19% | 211d | **DISQUALIFIED** | **DO NOT MODEL**: Extreme 211-day gap |
| `onion` | **Tirupati** | Tirupati | 903d | 92 | 811 | 10.19% | 211d | **DISQUALIFIED** | **DO NOT MODEL**: Extreme 211-day gap |
| `potato` | **Vijayawada** | NTR | 1017d | 573 | 444 | 56.34% | 40d | **DISQUALIFIED** | **DO NOT MODEL**: Density <60%; 40-day outage |
| `potato` | **Guntur** | Guntur | 1007d | 111 | 896 | 11.02% | 99d | **DISQUALIFIED** | **DO NOT MODEL**: 99-day reporting outage |
| `potato` | **Tirupati** | Tirupati | 1007d | 111 | 896 | 11.02% | 99d | **DISQUALIFIED** | **DO NOT MODEL**: 99-day reporting outage |

---

## 3. Clear Determination: What to Model vs. What NOT to Model

### Green-Light Series (Approved for ML Phase 1 Modeling)
The following 5 crop-mandi combinations represent authentic trading hubs with high liquidity, steady daily arrivals, over 80% calendar coverage, and no reporting gap exceeding 8 calendar days:
1. **Guntur Mandi — Banana** (821 trading days, 80.7% coverage)
2. **Vijayawada Mandi — Banana** (821 trading days, 80.7% coverage)
3. **Madanapalle Mandi — Tomato** (822 trading days, 80.8% coverage, Asia's major tomato clearinghouse)
4. **Kurnool Mandi — Onion** (822 trading days, 80.8% coverage, primary Rayalaseema onion market)
5. **Kurnool Mandi — Potato** (822 trading days, 80.8% coverage, active cold-storage depot)

### Strict Exclusion: DO NOT MODEL
The remaining 14 combinations are **strictly disqualified from machine learning modeling**:
- **Banana in Anantapur**: Contains an unbroken 209-day reporting blackout. Any time-series model (ARIMA, LightGBM, LSTM) attempting to forecast across this gap would hallucinate or fit noise.
- **Potato in Guntur & Tirupati**: Guntur and Tirupati are consumption markets for potatoes, not agricultural production or wholesale auction hubs. Records appear on only ~11% of calendar days with 99-day outages.
- **Onion in Madanapalle & Tirupati**: Madanapalle specializes in tomatoes, not onions. Sporadic onion arrivals yield only 92 days across 2.5 years (211-day gap).
- **Secondary Markets (<60% coverage, 40-day gaps)**: Guntur Tomato, Vijayawada Tomato/Onion/Potato. While prices can be displayed on the UI as static past lookups, time-series forecasting models must not be fitted on these broken series. For these mandis, the platform will display nearby hub proxy prices (e.g. Madanapalle for Tomato) rather than training low-confidence local models.

---

## 4. Cleaning Pipeline Audit & Data Hygiene Metrics

The pipeline processed **9,305 raw Agmarknet records**:
- **Unit Conversions (9,305 records)**: Fixed raw Agmarknet prices from ₹/quintal into consumer & farmer units (₹/kg) and standardized arrival volumes to metric tonnes.
- **Duplicates Resolved (4 records)**: Deduplicated across compound primary key `(mandi_id, crop_id, price_date, variety, grade)`. Retained the record with higher arrival volume.
- **Variety Normalizations (33 records)**: Standardized misspellings and regional synonyms (e.g., `Amritapani` $\rightarrow$ `Amruthapani`, `Hybrid Tomato` $\rightarrow$ `Hybrid`, `Red Onion` $\rightarrow$ `Red`, `Kufri Badshah` $\rightarrow$ `Kufri`).
- **Outliers Flagged & Kept (2 records, 0.022% outlier rate)**:
  - 1 severe data entry spike in Guntur Onion (₹280/kg, exceeding the ₹120/kg domain threshold).
  - 1 inverted price hierarchy record where minimum price exceeded maximum price.
  - In accordance with non-negotiable engineering principles, **neither record was deleted**. Both were preserved with `is_outlier = True` and documented reasons (`above_ceiling_120.0`, `min_greater_than_max`).
- **Final Cleaned Rows**: **9,301 valid records** saved in `data/processed/cleaned_mandi_prices.csv`.

---

## 5. Great Expectations Validation Results

Our expectation suite evaluated the processed dataset against 15 rigorous criteria:
- `expect_table_columns_to_match_set`: PASSED
- `expect_column_values_to_not_be_null` (`mandi_id`, `crop_id`, `price_date`, `modal_price_kg`, `min_price_kg`, `max_price_kg`): PASSED (0 nulls across 9,301 rows)
- `expect_column_values_to_be_in_set` (`crop_id` in `{banana, tomato, onion, potato}`; `grade` in `{FAQ, A, B, C, SUPER}`): PASSED
- `expect_column_values_to_be_between` (`modal_price_kg` on clean rows in [0.5, 250.0] ₹/kg; `arrival_tonnes` in [0, 5000]): PASSED
- `expect_compound_columns_to_be_unique` (`mandi_id`, `crop_id`, `price_date`, `variety`, `grade`): PASSED (0 duplicate rows)
- `expect_price_hierarchy_for_non_outliers` (`min_price <= modal_price <= max_price` on clean rows): PASSED (100% adherence)
- `expect_outlier_flag_integrity` (every outlier has a non-empty, traceable reason): PASSED

**Overall Suite Result**: **15 / 15 Passed (100.0% Success Rate)**.

---

## 6. Point-in-Time Features & Leakage Proof

The feature engineering pipeline in [`ml/features/feature_pipeline.py`](file:///c:/Users/chait/OneDrive/Desktop/GrowCircle/ml/features/feature_pipeline.py) generates 27 features point-in-time:
1. **Lags**: `price_lag_1d`, `price_lag_7d`, `price_lag_14d`, `price_lag_28d`, `price_diff_1d_7d`, `price_pct_change_7d`
2. **Rolling Statistics**: `rolling_mean_7d`, `rolling_std_7d`, `rolling_mean_28d`, `rolling_std_28d`
3. **Calendar**: `day_of_week`, `month`, `quarter`, `day_of_year`, `is_weekend`
4. **Holidays & Festivals**: `is_festival_today`, `days_to_next_festival`, `days_since_last_festival`
5. **Spatial Neighbours (<150km)**: `neighbour_modal_price_lag1`, `price_diff_to_neighbour_lag1`
6. **Arrivals**: `arrival_tonnes_lag1`, `arrival_rolling_mean_7d`
7. **Weather (Open-Meteo)**: `temp_max_c`, `temp_min_c`, `precipitation_mm` by mandi coordinates
8. **Fuel**: `diesel_price_rs_per_litre` (Andhra Pradesh retail rate as of $t-1$)

### Automated Leakage Test Verification
Tested in [`ml/tests/test_feature_leakage.py`](file:///c:/Users/chait/OneDrive/Desktop/GrowCircle/ml/tests/test_feature_leakage.py):
- **Future Injection Invariance**: Injected synthetic records on `as_of` and $as\_of + 1, 14\text{ days}$ with extreme values (₹5,000/kg). All 27 feature values remained **100% identical** down to the floating-point bit.
- **Past Modification Sensitivity**: Altering yesterday's price ($t-1$) dynamically altered `price_lag_1d` and rolling metrics, proving that the pipeline is responsive and not returning cached constants.
- **No Target Leakage**: Target price on `as_of` is strictly excluded from the feature vector.

---

## 7. MLOps: MLflow Tracking & Dataset Versioning

- **MLflow Tracking**: Configured to run locally using SQLite storage (`sqlite:///mlruns/mlflow.db`).
  - Active Experiment: `growcircle_mandi_price_foundation`
  - Active Run ID: `1db8606308404517a74a93f5fdf9356f`
  - Logged artifacts: Dataset schema, quality metrics, coverage summary, and data hash.
- **Dataset Registry (DVC-Compatible)**:
  - Catalog: [`ml/data/dataset_registry.json`](file:///c:/Users/chait/OneDrive/Desktop/GrowCircle/ml/data/dataset_registry.json)
  - Sidecar: [`data/processed/cleaned_mandi_prices.csv.dvc`](file:///c:/Users/chait/OneDrive/Desktop/GrowCircle/data/processed/cleaned_mandi_prices.csv.dvc)
  - Content Hash: `sha256:756ebd1bd30f1aebddbe6ab43593d41591a48e088c3fe1d6f8ee235bbf9657fd`
  - Owner: `GrowCircle ML Team`
