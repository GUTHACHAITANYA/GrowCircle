# ADR 0016: Post-Launch Machine Learning Monitoring, Safe Releases, and Trust Governance

## Context
Deploying machine learning models in Indian agricultural supply chains presents complex operational challenges once live:
1. **Silent Drift & Seasonality**: Crop cycles, monsoon anomalies, and policy shocks (e.g. government export bans on onions, unexpected Minimum Support Price revisions) alter underlying price and arrival distributions.
2. **Quantile Interval Miscalibration**: In volatile market crash weeks, forecast intervals can become overconfident, leaving smallholder farmers unprotected against price collapses.
3. **High Financial Stakes & Farmer Vulnerability**: Unlike recommendation engines in e-commerce, inaccurate agricultural guidance can cause severe direct financial loss.
4. **Dialect and Acoustic Drift**: Vernacular speech patterns and ambient field noise evolve across seasons, requiring continuous tracking of Voice Agent failure rates.
5. **Operating Cost Spikes**: Telephony (STT/TTS), LLM inference, and transactional SMS costs can grow uncontrollably without unit-level tracking and aggressive caching.

---

## Decisions

### 1. Multi-Dimensional Drift & Health Monitoring
- **Data & Prediction Drift**:
  - Employs **Two-Sample Kolmogorov-Smirnov (KS) tests** and the **Population Stability Index (PSI)** on numerical feature distributions and prediction outputs.
  - Features with $p < 0.05$ or $\text{PSI} \ge 0.25$ are flagged. Dataset drift is declared if $>33\%$ of features drift.
- **Daily Forecast Error Tracking as Actuals Arrive**:
  - Compares $P_{50}$ forecasts with realized mandi prices daily (MAE, sMAPE, Pinball loss).
  - Evaluates empirical interval coverage against the nominal 80% $[P_{10}, P_{90}]$ target.
  - Flags under-coverage ($<65\%$) or over-coverage ($>95\%$).
- **Computer Vision Confidence Shifts**:
  - Tracks confidence distributions on crop grading ($A/B/C$).
  - Alerts if low-confidence triage ($<0.65$) exceeds 20% or if blur/glare rates exceed 25%.
- **Voice Agent Multilingual Tracking**:
  - Tracks STT WER, intent error rates, hallucination attempts, and KVK escalation rates broken down across Telugu (`te`), Hindi (`hi`), Gujarati (`gu`), and English (`en`).

### 2. Multi-Tiered Alerting Engine
- Triggers actionable alerts across 3 severities (`INFO`, `WARNING`, `CRITICAL`):
  - **Forecast Error Breach**: sMAPE $> 25\%$ or MAE $> ₹5.0/\text{kg} \to$ `CRITICAL`.
  - **Data Ingestion Outage**: Active mandis drop by $> 40\% \to$ `CRITICAL`.
  - **Policy Shock & Festival Surges**: Detects structural price breaks (z-score $> 3.0$ with $>40\%$ jump) or active festival surge windows (Diwali, Sankranti) $\to$ `WARNING` / `INFO` (advising caution against hasty retraining).
  - **Budget Breach**: Daily or monthly spend approaching cap $\to$ `WARNING` at 80%, `CRITICAL` at 100%.

### 3. Safe Release Protocol: Shadow, Canary, and Automated Rollback
- No new model candidate is released directly to 100% of users.
- **Phased Lifecycle**:
  1. **Shadow Mode**: Candidate model executes in parallel on live requests; outputs are logged and benchmarked against baseline, but never shown to users.
  2. **Canary Mode**: Deterministic hash allocation (`hash(user_id) % 100 < canary_pct`) directs a small share of user traffic (e.g. 10%) to the candidate.
  3. **Automated Rollback Engine**: Real-time guardrail evaluation instantly aborts the canary and restores 100% traffic to baseline if:
     - Candidate sMAPE degrades by $> 15\%$ vs baseline.
     - Candidate latency exceeds SLA ($> 250\text{ ms}$ or $2\times$ baseline).
     - Candidate error / crash rate exceeds $1.0\%$.
     - Any hallucination attempt is caught by the grounding validator.
  4. **MLflow Tracking**: Every deployed version, candidate, and rollback is logged in SQLite MLflow with its dataset hash, parameters, and benchmark metrics.

### 4. Human Feedback Loop & Evaluation Hardening
- Provides a frictionless 1-click or 1-key error reporting channel:
  - Phone IVR: Single keypress (**Key 9** or **Key 0**).
  - WhatsApp: Quick button (`"WRONG_ANSWER"`) or voice note flag.
  - Web: "Flag as Incorrect" button.
- User reports enter an agronomist review queue (`/monitoring/feedback/queue`).
- Verified errors are promoted into **golden regression test cases** (`data/feedback/human_eval_cases.json`) and run in CI on every commit.

### 5. Cost Accounting, Budget Caps & Aggressive Caching
- Unit-level cost accounting:
  - STT: ₹0.15/min | TTS: ₹0.10/min | LLM: ₹0.0015/1k input, ₹0.0030/1k output | SMS: ₹0.12/msg.
- Aggressive caching for audio prompts, Agmarknet daily prices, and forecast summaries with hit-rate and financial savings telemetry.
- Enforces strict daily (₹5,000) and monthly (₹100,000) operating budget caps.

### 6. Quarterly Review & Governance Cadence
- Quarterly audit across Data Quality, Regional & Smallholder Fairness, DPDP Privacy, and Baseline Outperformance.
- Decommissioning mandate: Any model that fails to outperform its non-ML baseline is demoted back to rules.

---

## Consequences

### Positive
- **Guaranteed Trustworthiness**: Prevents silent model degradation from harming farmers.
- **Zero Risk Deployments**: Shadow mode and automated canary rollbacks eliminate catastrophic production release incidents.
- **Continuous Learning from Field Errors**: Human feedback directly expands the automated test suite.
- **Predictable Cost Ceiling**: Unit cost tracking prevents ballooning telephony and LLM bills.

### Negative & Operational Tradeoffs
- Additional compute overhead to run shadow inferences concurrently.
- Agronomist and ML engineer operational time required to review flagged feedback items quarterly.

---

## Status
**ACCEPTED** - Implemented in `ml/monitoring/`, exposed via FastAPI (`/monitoring`), and verified with comprehensive unit and integration tests.
