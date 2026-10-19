# GrowCircle Quarterly Machine Learning Review & Governance Checklist

**Document**: `docs/ml/review_checklist.md`  
**Applicability**: All Production Machine Learning Models (Phases ML-0 through ML-7)  
**Review Frequency**: Quarterly (Every 90 Days)  
**Required Signatories**: 
1. Lead Machine Learning Engineer
2. Platform Operations & Logistics Lead
3. Lead Agronomist / KVK Liaison Officer
4. Data Protection & Grievance Redressal Officer (DPDP Act 2023)

---

## 1. Executive Summary & Purpose

Machine learning models deployed in rural agricultural supply chains degrade over time due to seasonal crop cycles, climate events, changing state policies (minimum support prices, export bans), and evolving vernacular dialects.

This quarterly review enforces an uncompromising governance standard:
> **Core Principle**: If a model fails any data quality, fairness, or privacy gate, or if it no longer decisively beats its non-ML baseline, it is **immediately demoted or rolled back** to the rule-based / seasonal baseline.

---

## 2. Checklist Matrix

### Item 1: Data Quality & Ingestion Freshness

- [ ] **Mandi Data Freshness**:
  - [ ] Are 95%+ of active mandis reporting daily prices within 24 hours of market close?
  - [ ] Have all data arrival outages (>40% reporting drops) been investigated and logged?
- [ ] **Outlier Handling Integrity**:
  - [ ] Verify that the "Flag and Keep" policy is strictly preserved.
  - [ ] Confirm that **zero** anomalous rows were silently deleted from `data/raw` or database tables.
- [ ] **Feature Point-in-Time Correctness**:
  - [ ] Audit feature pipelines (`ml/features/`) to guarantee strict temporal filtering (`as_of` timestamp).
  - [ ] Run automated feature leakage tests: `pytest ml/tests/test_feature_leakage.py` (Must pass 100%).
- [ ] **Schema & Data Tests**:
  - [ ] Run Great Expectations / Pydantic validation suite.
  - [ ] Success rate on schema expectations must be $\ge 98.0\%$.

### Item 2: Fairness Across Regions, Crops & Smallholders

- [ ] **Regional Error Parity**:
  - [ ] Compare forecast error across agro-climatic zones:
    $$\frac{|\text{sMAPE}_{\text{Rayalaseema}} - \text{sMAPE}_{\text{Coastal Andhra}}|}{\text{sMAPE}_{\text{Coastal Andhra}}} \le 0.15$$
  - [ ] If regional error disparity exceeds 15%, regional proxy models must be recalibrated.
- [ ] **Crop Coverage Parity**:
  - [ ] Verify that high-volume cash crops (Tomato, Banana) do not monopolize model retraining resources over essential staples (Onion, Potato, Chilli).
- [ ] **Smallholder Direct-Selling Parity (Four-Fifths Rule)**:
  - [ ] Audit buyer-farmer ranking exposure logs:
    $$\text{Exposure Ratio} = \frac{\% \text{ Smallholders in Top-3 Recommendations}}{\% \text{ Smallholders in Available Pool}} \ge 0.80$$
  - [ ] Confirm zero disparate impact against marginal farmers ($<2$ hectares).
- [ ] **Driver Allocation Equity (Gini Coefficient)**:
  - [ ] Audit logistics dispatch logs (`/logistics/rank-drivers`).
  - [ ] Verify that driver allocation inequality Gini coefficient remains $< 0.35$.
  - [ ] Confirm fatigue dampening penalty $\exp(-N_{\text{recent}}/\tau)$ is active.

### Item 3: Privacy, Consent & DPDP Act 2023 Compliance

- [ ] **Statutory Consent Verification**:
  - [ ] Audit audio recordings and farm photos stored in training buckets.
  - [ ] Confirm 100% of training assets have explicit, timestamped statutory consent via `/agent/consent-recording` or `/dpdp/consent`.
  - [ ] Zero unconsented voice notes or camera photos in any dataset.
- [ ] **PII Scrubbing & Redaction Audit**:
  - [ ] Inspect raw and transformed call transcripts and chat logs.
  - [ ] Verify zero 10-digit Indian mobile numbers, 12-digit Aadhaar numbers, or 10-character PAN identifiers.
- [ ] **Right to Erasure (Account Deletion) Audit**:
  - [ ] Verify all accounts deleted via `/dpdp/delete-account` have had their PII cryptographically anonymized and unlinked from model training logs.

### Item 4: Continuous Superiority Over Baselines

Every ML model must be audited against its non-ML heuristic baseline. If an ML model fails to decisively beat the baseline, it is **demoted immediately**.

| Model & Phase | Active ML Architecture | Benchmark Baseline | Required Outperformance Margin | Action if Margin Fails |
| :--- | :--- | :--- | :---: | :--- |
| **ML-1: Price Forecaster** | LightGBM Global Multi-Horizon Quantile | Seasonal Naive (same weekday) & Naive Last-Value | **sMAPE $\ge 10\%$ better** than Seasonal Naive | Fallback to Seasonal Naive baseline |
| **ML-2: Anomaly Detector** | Residual Robust Z-Score + Isolation Forest | Rule Layer (10x jump, negative, min > max) | **Precision $\ge 85\%$, Recall $\ge 90\%$** | Auto-quarantine on rule layer only |
| **ML-3: Crop Planning** | Multi-Factor Cobweb Downside Risk Engine | 5-Year Historical Average Net Margin | **Downside VaR risk captures 90%+ crashes** | Revert to KVK static crop calendar |
| **ML-4: Computer Vision** | Transfer-Learned EfficientNet / ViT Grading | Simple Human Rule (aspect ratio + color histogram) | **Accuracy $\ge 15\%$ higher** than human heuristic | Require manual photo review by buyer |
| **ML-5: Smarter Matching** | LightGBM LambdaRank Listwise Ranker | Multi-Criteria Weighted Rules | **NDCG@3 $\ge 0.05$ higher** AND $\ge 1,200$ sessions | Revert to transparent rule-based ranker |
| **ML-6: Voice & Chat Agent** | Tool-Grounded Pipeline + Curated RAG | Unconstrained Generative LLM | **0.0% Hallucinations (Zero invented numbers)** | Disconnect voice execution; route to IVR menu |

### Item 5: Human Feedback Loop & Evaluation Bank Updates

- [ ] **Review Queue Clearance**:
  - [ ] Have all user error reports submitted via IVR keypress 9, WhatsApp "WRONG_ANSWER", or Web flag been reviewed by an agronomist?
- [ ] **Golden Test Case Promotion**:
  - [ ] Verify that confirmed error reports were transformed into golden regression test cases (`data/feedback/human_eval_cases.json`).
  - [ ] Confirm these cases are executed on every git push in CI.

### Item 6: Cost, Budget & Caching Efficiency

- [ ] **Unit Telephony Cost Health**:
  - [ ] STT cost per call $< ₹0.25$.
  - [ ] TTS cost per call $< ₹0.20$.
  - [ ] Average call turn cost $< ₹0.60$.
- [ ] **Cache Efficiency**:
  - [ ] Mandi price cache hit rate $\ge 75\%$.
  - [ ] Audio prompt synthesis cache hit rate $\ge 60\%$.
- [ ] **Budget Cap Compliance**:
  - [ ] Total monthly operational spend within the ₹100,000 ceiling.

---

## 3. Quarterly Review Sign-Off Form

**Review Quarter**: Q___ 2026  
**Review Date**: ____________________  

| Role | Name | Decision (`APPROVED` / `ROLLBACK_TRIGGERED`) | Signature |
| :--- | :--- | :---: | :--- |
| **ML Lead** | ____________________ | ____________________ | ____________________ |
| **Operations Lead** | ____________________ | ____________________ | ____________________ |
| **KVK Agronomist** | ____________________ | ____________________ | ____________________ |
| **DPDP Officer** | ____________________ | ____________________ | ____________________ |

> [!CAUTION]
> If any signatory selects `ROLLBACK_TRIGGERED`, the model is placed into shadow mode or replaced by its verified rule baseline within 2 hours of sign-off.
