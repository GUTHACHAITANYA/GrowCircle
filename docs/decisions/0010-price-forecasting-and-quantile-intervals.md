# ADR 0010: Multi-Horizon Agricultural Price Forecasting, Calibrated Quantile Intervals, and 3-Tier Fallback Hierarchy

## Context
Agricultural spot prices across Indian APMC mandis are notoriously volatile, subject to perishability cycles, weather disruptions, local market arrivals, and festival demand shocks. Providing price guidance to farmers, buyers, and consumers requires forecasting modal prices across 1, 3, 7, and 14 days ahead.

However, standard machine learning forecasting in agriculture suffers from three fatal mistakes:
1. **False Certainty**: Point-only forecasts mislead smallholder farmers into expecting exact rupee outcomes. Forecasts must be probabilistic, delivering calibrated uncertainty ranges (10th to 90th percentiles).
2. **Ignoring Baselines**: Complex models frequently underperform trivial heuristics (like "same price as last week" or "7-day average") during steady regimes. A model must earn production deployment by strictly beating classical baselines on realistic time-series splits.
3. **Sparse Mandi Hallucinations**: Mandis with thin reporting, long data gaps, or fewer than 180 observations cannot sustain reliable series-specific models. Naively generating predictions for sparse mandis creates harmful misinformation.

---

## Decisions

### 1. Baselines as Mandatory Benchmarks
Before deploying any candidate ML model, 4 statistical baselines are implemented and evaluated per series:
- **Naive Forecaster**: Last observed modal price $\hat{y}_{t+h} = y_t$.
- **Seasonal Naive Forecaster**: Price on the same day-of-week 7 days prior $\hat{y}_{t+h} = y_{t+h-7}$.
- **7-day Moving Average**: Rolling mean over the prior 7 calendar days.
- **Holt-Winters Exponential Smoothing**: Additive level and trend smoothing.

A model is deployed only if its Mean Absolute Scaled Error (MASE relative to seasonal naive) is $< 1.0$ and MAE is lower than all baselines across the horizons.

### 2. Candidate Architecture: Direct Multi-Horizon Quantile LightGBM
- **Direct Multi-Horizon**: Rather than recursive autoregression (which compounds errors across 14 steps), separate direct models are trained for each horizon $h \in \{1, 3, 7, 14\}$.
- **Global Tabular Model**: A single unified LightGBM model trained across all eligible mandi-crop series, utilizing one-hot series embeddings alongside the 27 point-in-time features engineered in Phase ML-0 (lags, rolling stats, arrivals, spatial neighbors, weather, diesel fuel, and holiday flags).
- **Quantile Regressors**: For each horizon, three quantile regressors are fitted ($\alpha \in \{0.10, 0.50, 0.90\}$) using `objective="quantile"`, `alpha=q`.
- **Monotonicity Post-Processing**: LightGBM quantile models are evaluated independently; to eliminate quantile crossing, predictions are strictly sorted:
  $$\hat{y}_{10} \le \hat{y}_{50} \le \hat{y}_{90}$$

### 3. Evaluation: Expanding-Window Rolling-Origin CV
- **No Random Splits**: Temporal splits exclusively.
- **5 Evaluation Origins**: Cutoffs at 2026-03-01, 2026-04-15, 2026-06-01, 2026-07-15, and 2026-08-30 across all eligible AP hubs.
- **Metrics**: MAE, sMAPE, MASE (against seasonal naive), Pinball Loss (at 10%, 50%, 90%), and Empirical 80% Interval Coverage ($\% \in [\hat{y}_{10}, \hat{y}_{90}]$).
- **Slice Analysis**: Explicit tracking during volatile market regimes (periods where 7d price change $> 15\%$).

### 4. Deferral of Temporal Fusion Transformer (TFT) and N-BEATS
Deep learning architectures (Temporal Fusion Transformers, N-BEATS, PatchTST) were evaluated and explicitly deferred at pilot scale based on empirical and theoretical criteria:
- **Sample Size Constraint**: The eligible AP historical dataset contains ~820 daily observations per series (~4,100 total rows across 5 series). Transformers require $10^5-10^6$ observations to avoid catastrophic overfitting without severe pretraining.
- **Tabular Inductive Bias**: LightGBM naturally handles heterogeneous tabular features (weather, fuel, arrivals, discrete festival indicators) without complex embedding projections.
- **Operational Efficiency**: LightGBM trains in $< 2$ seconds and delivers sub-5ms CPU inference without GPU runtime dependencies, running seamlessly within lightweight containerized Celery worker tasks.
- **Empirical Superiority**: LightGBM achieves a 1-day MASE of **0.240** (76% error reduction over seasonal naive) and 80.0% coverage. TFT will be re-evaluated only if data volume expands $20\times$ across all Indian states and LightGBM plateaus.

### 5. 3-Tier Sparse Mandi Fallback Hierarchy
Every forecast request passes through a 3-tier resolution engine:
1. **Tier 1 (`mandi_ml`)**: Mandi has $\ge 180$ days of data, $< 21$ days max gap, and candidate ML beats baseline on backtest. Direct model is utilized.
2. **Tier 2 (`proxy_hub_ml`)**: Mandi is sparse or secondary, but situated in an active district. Forecasts fall back to the district/state primary price-discovery hub (e.g., Madanapalle for Tomato, Guntur for Banana, Kurnool for Onion/Potato).
3. **Tier 3 (`seasonal_naive_baseline`)**: Series does not have an established proxy hub or ML does not beat baseline. Seasonal naive baseline is returned directly.

Every response explicitly returns `data_sufficiency_level`, `model_used`, and `beats_baseline`.

### 6. Transparent API & Multi-lingual Guidance
- **Endpoint**: `GET /forecast?mandi_id=..&crop=..&horizon=7`
- **Output**: Returns `median_price_kg`, `range_10_90_kg`, `plain_note: "guidance only"`, `data_sufficiency_level`, and `beats_baseline`.
- **Directional Messages**: Natural language summaries formatted for Voice (IVR), WhatsApp, and App in English, Telugu, Hindi, and Gujarati with explicit uncertainty caveats (e.g., *"Prices may rise slightly next week, uncertain."*), never exact price promises.

### 7. Automated Nightly Retraining & MLflow Tracking
- Celery task `nightly_rescore_and_model_promotion` runs expanding-origin backtests nightly.
- Retrained model is promoted if and only if:
  $$\text{Backtest MAE}_{\text{candidate}} < \text{Backtest MAE}_{\text{active}}$$
- All runs, parameters, metrics, and serialized artifacts are tracked in local MLflow (`sqlite:///mlruns/mlflow.db`).

---

## Consequences & Verification
- **Benchmark Results**:
  - 1-Day: LightGBM MAE ₹1.38 vs Seasonal Naive ₹5.75 (MASE 0.240, 80.0% coverage).
  - 3-Day: LightGBM MAE ₹3.91 vs Seasonal Naive ₹8.15 (MASE 0.480, 72.0% coverage).
  - 7-Day: LightGBM MAE ₹3.21 vs Seasonal Naive ₹3.49 (MASE 0.919, 72.0% coverage).
  - 14-Day: LightGBM MAE ₹3.12 vs Seasonal Naive ₹6.57 (MASE 0.474, 88.0% coverage).
- **Test Suite**: 93/93 passing tests across the entire repository.
- **Model Card**: Formally published at [`docs/ml/model_cards/price_forecast.md`](file:///c:/Users/chait/OneDrive/Desktop/GrowCircle/docs/ml/model_cards/price_forecast.md).
