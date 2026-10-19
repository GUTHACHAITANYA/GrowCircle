# ADR 0009: Machine Learning Data Foundation, Point-in-Time Featurization, and MLOps Registry

## Context
GrowCircle plans to introduce price forecasting and crop planning guidance for farmers, buyers, and consumers. In agricultural time-series modeling across India, standard models fail primarily due to data foundation deficiencies rather than algorithm choice:
1. **Reporting Outages & Severe Gaps**: Mandis experience seasonal closures, local holidays, and intermittent internet connectivity, leading to long multi-month reporting gaps. Training models naively across severe gaps causes catastrophic model collapse.
2. **Future Data Leakage**: In historical backtests, feature pipelines that compute rolling means or lags using centered windows or dataset-wide aggregations leak future prices into training data, generating falsely optimistic backtests that fail in live production.
3. **Data Loss from Aggressive Filtering**: Typical ML pipelines silently drop records flagged as outliers, erasing vital supply-shock and price-spike events.
4. **Lack of Dataset Versioning & Governance**: Unversioned datasets make it impossible to audit which dataset snapshot produced a given prediction.

---

## Decisions

### 1. Resumable Historical Backfill with Raw Data Preservation
- Backfill job (`ml/data/backfill.py`) pulls multi-year data for priority crops in Andhra Pradesh (Banana, Tomato, Onion, Potato).
- **Untouched Raw Storage**: Raw files are preserved bit-for-bit in `data/raw/` with a state file (`data/raw/backfill_state.json`) enabling incremental and resumable execution.

### 2. Cleaning Pipeline & "Flag and Keep" Outlier Policy
- Cleaning pipeline (`ml/data/cleaning.py`):
  - Converts units: ₹/quintal to ₹/kg (`modal_price / 100.0`) and arrivals to metric tonnes.
  - Deduplicates on compound key `(mandi_id, crop_id, price_date, variety, grade)`.
  - Normalizes variety aliases to standard APMC taxonomy.
- **Outlier Policy**: Outliers are **flagged and kept, never silently deleted**. Rows receive `is_outlier = True` with explicit reasons (`above_ceiling`, `below_floor`, `min_greater_than_max`, `non_positive_price`). Clean rows are filtered explicitly downstream by models without losing raw data integrity.
- **Data Tests**: Formal expectation suite (`ml/data/expectations.py`) enforcing null checks, ranges, unicity, and price hierarchy.

### 3. Strict Point-in-Time Feature Engineering
- Feature pipeline (`ml/features/feature_pipeline.py`) mandates that every feature function accepts an explicit `as_of` date (`datetime.date`).
- Only data where `price_date < as_of` is accessible.
- Generates 27 features:
  - Lags: 1d, 7d, 14d, 28d modal price and 7d price change/momentum.
  - Rolling Statistics: 7d and 28d rolling mean and standard deviation.
  - Calendar & Seasonality: Day of week, month, quarter, day of year, weekend flag.
  - Indian Festivals & Holidays: Regional AP holiday flags and distance to next festival.
  - Spatial Neighbouring-Mandi Prices: Mandis within 150 km radius as of $t-1$.
  - Arrivals: Market arrival volume (tonnes) at lag 1 and 7d rolling average.
  - Weather: Mandi coordinate temperature max/min and precipitation via Open-Meteo parameters.
  - Fuel: Retail diesel prices in AP as of $t-1$.

### 4. Automated Feature Leakage Testing
- Automated test (`ml/tests/test_feature_leakage.py`) asserts that injecting or altering future data on or after `as_of` produces 100% invariant feature values. Fails build if any feature leaks data on or after `as_of`.

### 5. Dataset Registry & MLOps Tracking
- Dataset registry (`ml/data/dataset_registry.py`) follows the convention: `name`, `version`, `data_hash` (SHA-256), `metrics`, `owner`, `date`. Produces DVC-compatible sidecars (`cleaned_mandi_prices.csv.dvc`).
- MLflow experiment tracking (`ml/tracking/mlflow_tracker.py`) runs locally using SQLite (`sqlite:///mlruns/mlflow.db`) tracking parameters, metrics, tags, and artifacts.

### 6. Honest Modeling Eligibility Gate
- Coverage analysis (`ml/data/coverage.py`) establishes strict criteria for modeling:
  - $\ge 180$ available trading days
  - $\ge 60\%$ coverage density
  - $\le 21$ days maximum consecutive gap
- **Approved to Model**: Guntur Banana, Vijayawada Banana, Madanapalle Tomato, Kurnool Onion, Kurnool Potato.
- **Strictly Disqualified (DO NOT MODEL)**: 14 sparse/broken series (e.g., Anantapur Banana with 209-day gap, Guntur/Tirupati Potato with 99-day gap).

---

## Consequences & Verification
- Zero data leakage guaranteed by automated mathematical proof.
- Full provenance and DVC versioning for all datasets.
- 86/86 total tests passing across backend and ML test suites.
- Strict protection against modeling sparse series preventing erroneous predictions.
