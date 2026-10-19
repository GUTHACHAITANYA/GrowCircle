# ADR 0011: Multi-Layer Anomaly Detection, Quarantining, and Outage Monitoring

## Context
GrowCircle serves as the single source of truth for mandi prices and direct farm-to-institution trading. In agricultural marketplaces, erroneous data causes severe harm:
1. **Clerical & Portal Errors**: Mandi data entry operators frequently enter ₹/quintal into ₹/kg fields (e.g. ₹2500/kg instead of ₹25/kg) or make 10x typographical errors (e.g. typing an extra zero), confusing farmers and misleading price forecasting models.
2. **Upstream Source Outages**: Ingestion portals (data.gov.in / Agmarknet) intermittently suffer silent partial outages where reporting drops from 20 mandis to 2, leading downstream applications to assume markets are closed.
3. **Marketplace Negotiation Abuse**: Unchecked negotiation flows allow predatory buyers to spam 70% lowball offers, bad-faith traders to repeatedly cancel deals, and fraudulent accounts to upload recycled stock photos instead of fresh farm lots.

---

## Decisions

### 1. Two-Layer Price Anomaly Detection with Auto-Clearing
- **Layer 1: Deterministic Rule Guard**:
  - Catches non-positive prices, inverted ranges (`min > max`), modal prices out of bounds, unit errors ($\ge 450$ ₹/kg for banana/tomato), and 10x sudden jumps relative to 7d moving average.
  - Severity assigned: `CRITICAL` or `HIGH`. Rule violations cannot be auto-cleared.
- **Layer 2: Statistical Layer**:
  - Robust Z-Score on forecast residuals: $Z = |e_t - \text{median}(e)| / (1.4826 \cdot \text{MAD})$. Flags if $Z \ge 3.5$.
  - Per-Crop Multivariate Isolation Forest: evaluates log price, ratio to 7d MA, 1d price change, spread ratio, and arrival volume.
- **Auto-Clearing Heuristic**:
  - If a statistical anomaly is corroborated by $\ge 1$ neighboring mandi within 150km showing a $\ge 12\%$ shift in the same direction, or by a $\ge 300\%$ arrival surge explaining a price drop, it is recognized as a legitimate physical market event and auto-cleared.

### 2. Strict Quarantine & Admin Review Queue
- Flagged rows are assigned `status: "pending_review"` and linked to `anomaly_reviews` table.
- **Quarantine Guarantee**: Public endpoints (`GET /prices`) strictly filter `WHERE anomaly_status IN ('clean', 'approved', 'auto_cleared')`. Unreviewed anomalies are never shown to farmers, buyers, or consumers.
- **Admin Workflow**:
  - `GET /admin/anomalies/queue`: Lists pending items with diagnostics and metrics payload.
  - `POST /admin/anomalies/{id}/review`: Admin executes `approve` (releasing to users) or `reject` (permanently hiding), generating an immutable entry in `audit_logs`.

### 3. Reporting Drop & Source Outage Detector
- Learns the expected mean $\mu_d$ and standard deviation $\sigma_d$ of active reporting mandis for each day of the week $d \in \{0, \dots, 6\}$.
- Distinguishes expected weekend closures (Sunday baseline $\mu \approx 2.0$) from true outages.
- Triggers `CRITICAL_OUTAGE` when weekday reporting drops $\le 35\%$ of baseline or $Z_{\text{drop}} \ge 3.0$, alerting operators to possible data.gov.in downtime.

### 4. Marketplace & Deal Integrity
- Flags offers deviating $> 40\%$ from prevailing mandi spot prices (`DEAL_OFFER_EXTREME_LOWBALL`).
- Flags users with serial cancellations ($\ge 3$ cancellations and $\ge 50\%$ rate in 7 days).
- Detects produce listing photo theft by matching image SHA-256 hashes against prior uploads from different farmers.

### 5. Evaluation Benchmark & Honest Limitations
- Benchmarked against 250 curated, hand-labelled instances (`data/anomaly_evaluation_sample.csv`):
  - Overall Precision: **97.7%**
  - Overall Recall: **88.4%**
  - F1-Score: **92.8%**
  - Specificity: **98.7%**
- **Honest Limitations Declared**:
  - Sample size ($N=250$) has an estimated confidence margin of $\pm 4.5\%$ at 95% confidence.
  - Rare black-swan shocks (national export bans, extreme floods) require ongoing active learning via human admin reviews in the review queue.

---

## Consequences & Verification
- **All 110 tests passing** across unit, integration, and ML suites.
- Erroneous data quarantined before reaching end-user interfaces.
- Model Card published at [`docs/ml/model_cards/anomaly_detection.md`](docs/ml/model_cards/anomaly_detection.md).
