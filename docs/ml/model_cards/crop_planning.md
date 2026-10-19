# Model Card: GrowCircle Crop Planning Guidance & Price-Crash Risk Engine

**Model Name**: `Cobweb Crowding & Agro-Climatic Crop Planning Guidance Engine`  
**Model Version**: `crop_plan_v1`  
**Date**: October 2026  
**Primary Developers**: GrowCircle Machine Learning & Agricultural Economics Team  
**License**: Apache-2.0  
**Statutory Warning**: *"Guidance only; check with your local agriculture officer or KVK before finalizing seed purchases."*

---

## 1. Intended Use & Target Beneficiaries

- **Primary Purpose**: Pre-season planting guidance for smallholder and marginal farmers across Andhra Pradesh. Ranks 3 to 5 candidate crops by expected net profit per acre and explicitly calculates downside exposure to supply gluts and price crashes.
- **Target Users**:
  - Smallholder farmers deciding which crop to plant in their upcoming cultivation window.
  - Farmer Producer Organisations (FPOs) coordinating acreages across member farmers to prevent village-level gluts.
  - Village agricultural extension helpers and KVK officers assisting farmers during input procurement.
- **Strict Out-of-Scope Uses**:
  - Binding commercial contract farming guarantees.
  - Micro-finance credit underwriting without physical officer verification.
  - Speculative commodity trading or crop futures arbitrage.

---

## 2. Hard Agronomic Guardrails (ANGRAU & KVK Verification)

- **Absolute Rule**: The system **never** recommends a crop whose agronomic suitability for the target district and planting month is not confirmed by a verified scientific institution:
  - **Acharya N.G. Ranga Agricultural University (ANGRAU)** Agro-Climatic Zone Recommendations.
  - **Dr. Y.S.R. Horticultural University (YSRHU)** Horticulture Guidelines.
  - **ICAR Krishi Vigyan Kendra (KVK)** District Contingency Plans.
- **Variety Recommendations**: Each candidate provides verified KVK varieties (e.g., *Grand Naine* for Banana, *Bhima Super* for Onion, *LCA 334* for Chilli, *Arka Rakshak* for Tomato).

---

## 3. Data Foundation & Government Open Data Licenses

| Dataset | Primary Source | Government License | Purpose in Engine |
| :--- | :--- | :--- | :--- |
| **Mandi Price History & Seasonality** | Agmarknet / MoA&FW | Open Access (data.gov.in) | Harvest window price distribution ($p_{10}, p_{50}, p_{90}$) |
| **District Acreage & Production** | Directorate of Economics & Statistics AP | Government Open Data License - India (GODL) | Cobweb crowding index and district area share |
| **Scale of Finance Norms** | State Level Bankers' Committee (SLBC) AP | Public Financial Norms (2024–2026) | Baseline cost ranges ($c_{10}, c_{50}, c_{90}$) |
| **District Yield Statistics** | Department of Agriculture AP / DES | GODL - India | Baseline yield ranges ($y_{10}, y_{50}, y_{90}$) |
| **Farmer Diary Ledger** | GrowCircle `FarmSeason` & `FarmDiaryEntry` | Farmer Private Data (DPDP Act 2023 Consent) | 50/50 blending of personal cost & yield |

---

## 4. Algorithmic Mechanics: Cobweb Crowding & Price Crash Risk

### The Cobweb Dilemma in Indian Horticulture
When a cash crop commands elevated prices at planting time ($P_{\text{plant}} > P_{\text{hist}}$), uncoordinated farmers massively expand sown area. At harvest time, supply surges beyond mandi intake capacity, leading to catastrophic market crashes (e.g., Tomato crashing from ₹45/kg to ₹3.80/kg in Rayalaseema mandis).

### Mathematical Formulation
1. **Cobweb Crowding Factor**:
   $$\text{Crowding Factor} = \left(\frac{P_{\text{plant}}}{P_{\text{hist\_avg}}}\right)^{0.5} \times \left(1.0 + \frac{\text{District Area Share}}{0.15}\right) \times (1.0 + \Delta_{\text{trend\_3yr}})$$
2. **Price Crash Risk Score ($0 \text{ to } 100$)**:
   $$\text{Score} = \min\left(100, \text{round}\left(35 \cdot (\text{Crowding} - 0.7) + 25 \cdot \text{Perishability} + 20 \cdot \text{Volatility}\right)\right)$$
   - `LOW` ($0 \le \text{Score} \le 29$): Stable demand, diversified acreage.
   - `MEDIUM` ($30 \le \text{Score} \le 54$): Moderate crowding; inter-state trade buffer.
   - `HIGH` ($55 \le \text{Score} \le 74$): Heightened supply glut alert.
   - `SEVERE` ($75 \le \text{Score} \le 100$): Severe crash risk; over-planting detected.
3. **Asymmetric Downside Price Penalty**:
   When $\text{Crowding Factor} > 1.0$, the harvest window bottom 10th percentile price ($p_{10}$) is discounted by $(1 / \text{Crowding}^{0.8})$, ensuring downside profit estimates reflect market crash conditions.

---

## 5. Output Policy: Ranges Always, Never Single Numbers

To prevent dangerous over-confidence, single numbers are prohibited across all interfaces:
- **Harvest Price Range**: $[p_{10}, p_{50}, p_{90}]$ in ₹/kg.
- **Yield Range**: $[y_{10}, y_{50}, y_{90}]$ in tonnes/acre.
- **Cost Range**: $[c_{10}, c_{50}, c_{90}]$ in ₹/acre.
- **Profit Range**:
  - **Downside (Pessimistic 10th)**: $(y_{10} \times 1000 \times p_{10}) - c_{90}$ (Crashed price + poor yield + high cost).
  - **Expected (Median 50th)**: $(y_{50} \times 1000 \times p_{50}) - c_{50}$.
  - **Upside (Optimistic 90th)**: $(y_{90} \times 1000 \times p_{90}) - c_{10}$ (Peak price + high yield + lean cost).

---

## 6. Historical Multi-Season Backtest Evaluation

Evaluated across 6 historical production seasons (2024–2025):
- **Total Seasons Tested**: 6
- **Crashes Encountered**: 1 (Kharif 2024 Rayalaseema Tomato crash)
- **Crashes Successfully Warned**: 1
- **Glut Crash Avoidance Rate**: **100.0%**
- **False Alarm Count**: 2 (Late Kharif 2024 Guntur Chilli, Late Kharif 2025 Annamayya Tomato)
- **Overall Season Accuracy**: **66.7%**

### Honest Failure Mode Disclosure: Why False Alarms Occur
In 2 out of 6 seasons, the model flagged high crash risk because district acreage was heavily crowded. However, **unseasonal cyclones and floods in neighboring states (Maharashtra and Karnataka)** damaged competing production, causing a national supply deficit and driving prices unexpectedly higher.
> **Key Lesson**: Regional planting models cannot foresee weather shocks in competing production belts 3 months before harvest. Warning farmers of downside risk remains the safer fiduciary recommendation than letting them blindly enter a local glut.

---

## 7. Multilingual Voice Guidance (< 45 Seconds)

All outputs generate audio summaries under 45 seconds (~60 to 75 words) in:
- **English (`en`)**: Clear concise advisory with KVK referral.
- **Telugu (`te`)**: Local vernacular terms (అరటి, ఉల్లి, మిరప, దిగుబడి, నష్ట భయం).
- **Hindi (`hi`)**: Clear Hindi guidance with KVK mention.
- **Gujarati (`gu`)**: Accessible Gujarati translation for Western zones.
