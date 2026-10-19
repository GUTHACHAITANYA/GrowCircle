# ADR 0012: Crop Planning Guidance, Downside Risk Modelling, and Crash Avoidance

## Context
In Indian agriculture—particularly horticulture across Andhra Pradesh (Rayalaseema and Coastal districts)—farmers frequently suffer catastrophic price crashes driven by the classic **Cobweb Theorem (supply gluts)**:
1. **Lagged Supply Response**: High prices at planting time signal to hundreds of thousands of independent farmers to plant the same cash crop (e.g. Tomato or Green Chilli).
2. **Synchronized Harvest Glut**: 3 to 5 months later, peak harvests hit mandis simultaneously, overwhelming cold storage and transport buffers, crashing prices below cost-of-cultivation (e.g. Tomato falling to ₹3.80/kg in Madanapalle/Annamayya mandis).
3. **Misleading Single Numbers**: Traditional advisory systems give misleading single numbers (e.g. "Expected profit: ₹3,00,000/acre"), hiding downside exposure from weather risks, yield variances, and market gluts.
4. **Agronomic Feasibility Risks**: Generic planning models risk recommending crops unsuited to the local soil, agro-climatic zone, or planting calendar.

---

## Decisions

### 1. Mandatory Agronomic Suitability Verification (ANGRAU & KVK Guardrail)
- **Hard Filter**: Under no circumstances does GrowCircle recommend a crop whose agronomic suitability for that specific district and planting month is not confirmed by an authoritative source:
  - **Acharya N.G. Ranga Agricultural University (ANGRAU)** Agro-Climatic Zone Recommendations.
  - **Dr. Y.S.R. Horticultural University (YSRHU)** horticultural crop guidelines.
  - **ICAR Krishi Vigyan Kendra (KVK)** district contingency plans.
- Candidate crops are tagged with specific KVK-recommended high-yield varieties (e.g. Grand Naine for Banana, Bhima Super for Onion, LCA 334 for Chilli).

### 2. Multi-Source Data Foundation & Open Government Licenses
- **Price History & Seasonality**: Daily modal Agmarknet mandi prices (2024–2026) cleaned with Phase ML-0/ML-2 pipeline.
- **District Area & Production Statistics**: Directorate of Economics & Statistics (DES AP) and Ministry of Agriculture & Farmers Welfare (MoA&FW) datasets released under the **Government Open Data License - India (GODL)**.
- **Cost-of-Cultivation Norms**: State Level Bankers' Committee (SLBC) Andhra Pradesh – *Scale of Finance 2024–2026* for crop loans, broken down into input costs (seeds, fertilizer, plant protection), labour, and machinery.
- **Farmer Diary Blending**: When a registered farmer has logged cultivation seasons and entries in `farm_seasons` and `farm_diary_entries`, the engine blends 50% farmer personal costs/yields with 50% regional SLBC norms, marking `data_sufficiency: "blended_farmer_diary"`.

### 3. Cobweb Crowding & Price-Crash Risk Engine
- **Crowding Multiplier**:
  $$\text{Crowding Factor} = \left(\frac{P_{\text{plant}}}{P_{\text{hist\_avg}}}\right)^{0.5} \times \left(1.0 + \frac{\text{Area Share}}{0.15}\right) \times (1.0 + \Delta_{\text{trend\_3yr}})$$
- **Crash Risk Score (0–100)**:
  $$\text{Score} = \min\left(100, \text{round}\left(35 \cdot (\text{Crowding} - 0.7) + 25 \cdot \text{Perishability} + 20 \cdot \text{Volat}\right)\right)$$
  Classified into tiers: `LOW` (0–29), `MEDIUM` (30–54), `HIGH` (55–74), `SEVERE` (75–100).
- **Asymmetric Downside Penalty**:
  When crowding factor $> 1.0$, the bottom 10th percentile price ($p_{10}$) is penalized by $(1 / \text{Crowding}^{0.8})$, protecting farmers from false optimism.

### 4. Ranges Always, Never Single Numbers
All outputs are strictly presented as three-quantile ranges `[10th percentile, 50th percentile, 90th percentile]`:
- Harvest Mandi Price: $[p_{10}, p_{50}, p_{90}]$ in ₹/kg.
- Yield per Acre: $[y_{10}, y_{50}, y_{90}]$ in tonnes/acre.
- Cultivation Cost per Acre: $[c_{10}, c_{50}, c_{90}]$ in ₹/acre.
- Net Profit per Acre:
  - Downside: $(y_{10} \times 1000 \times p_{10}) - c_{90}$
  - Expected: $(y_{50} \times 1000 \times p_{50}) - c_{50}$
  - Upside: $(y_{90} \times 1000 \times p_{90}) - c_{10}$

### 5. Statutory Advisory Label & Multilingual Voice Synthesis
- Every API response and screen prominently displays:
  `"Guidance only; check with your local agriculture officer or KVK before finalizing seed purchases."`
- Provides short spoken audio summaries (< 45s audio duration) in **English**, **Telugu**, **Hindi**, and **Gujarati**.

### 6. Multi-Season Historical Backtest & Honest Failure Reporting
- Evaluated across 6 historical seasons (2024–2025):
  - **100% Glut Crash Avoidance**: Successfully flagged the Kharif 2024 Rayalaseema Tomato crash, warning farmers of severe downside risk.
  - **Honest False Alarm Reporting**: Documented 2 false alarms (e.g. Late Kharif 2024 Guntur Chilli and Late Kharif 2025 Annamayya Tomato) where high local planting pointed to a crash, but unseasonal cyclones in competing states (Maharashtra/Karnataka) caused an unexpected national supply deficit.

---

## Consequences
- **Positive**: Protects farmers from synchronized over-planting; prevents severe financial loss; reinforces trust through transparent downside ranges.
- **Operational**: Requires quarterly updates to district acreage datasets and annual updates to SLBC Scale of Finance.
- **Crowdsourcing Call-to-Action**: Identifies the need for real-time farmer intention data to reduce external weather false alarms.
