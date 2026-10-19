# Model Card: GrowCircle Smart Matching & Rural Logistics Optimization Engine

**Model Name**: `GrowCircle Smart Matching & Rural Logistics Engine (ML-5)`  
**Model Version**: `matching_logistics_v1`  
**Date**: October 2026  
**Primary Developers**: GrowCircle Machine Learning & Operations Research Team  
**License**: Apache-2.0  
**Statutory Warning**: *"Guide rates and rankings are indicative decision-support tools. Transporters, buyers, and farmers agree directly on commercial freight terms without platform commissions."*

---

## 1. Intended Use & Target Beneficiaries

- **Primary Purpose**:
  - Pair buyer purchase requirements with rural smallholder produce listings using verifiable multi-criteria matching and listwise ranking.
  - Compute transparent, fair transport rate ranges $[R_{\min}, R_{\text{est}}, R_{\max}]$ to prevent freight price-gouging in rural corridors.
  - Solve multi-stop vehicle pickup routing using **Google OR-Tools** (CVRPTW) under vehicle capacity, pickup time windows, and crop spoilage shelf-life constraints (e.g. Tomato 18h, Banana 36h), reducing farmer logistics costs per kilogram.
  - Dispatch verified transport drivers with anti-monopoly fairness dampening so trips are equitably distributed across local drivers.
- **Target Beneficiaries**:
  - Smallholder and marginal farmers (<2 hectares) in Andhra Pradesh.
  - Institutional and bulk direct buyers (mess halls, hostels, retail aggregators).
  - Local rural vehicle operators (Goods Auto, Tata Ace mini-trucks, larger regional trucks).
- **Out-of-Scope Uses**:
  - Mandatory price fixing or algorithmic wage suppression for drivers.
  - High-frequency automated algorithmic trading.

---

## 2. Component Architecture & Formulation

### 2.1 Buyer-Farmer Ranking (LambdaRank vs Rule Baseline)

- **Rule Baseline Ranker**:
  $$\text{Score}_{\text{rule}} = 0.30 \cdot \text{DistanceScore} + 0.20 \cdot \text{QtyFit} + 0.15 \cdot \text{GradeFit} + 0.15 \cdot \text{PriceFit} + 0.10 \cdot \text{CompletionRate} + 0.10 \cdot \left(\frac{\text{Rating}}{5.0}\right)$$
- **LightGBM LambdaRank Model**:
  - Listwise gradient ranking directly optimizing NDCG.
  - Features: `distance_km`, `quantity_fit`, `grade_fit`, `price_fit_vs_mandi`, `completion_rate`, `response_time_hours`, `rating_norm`, `is_smallholder`.
  - Implicit feedback relevance labeling:
    - 0: Ignored / high complaint
    - 1: Viewed only
    - 2: Accepted offer
    - 3: Completed deal
    - 4: Completed on-time with 0 complaints
- **Offline Evaluation**:
  - Evaluated on test sessions with **NDCG@3**.
- **A/B Testing Gate**:
  - Deterministic 50/50 hashing by `query_id` (`Variant A: rules`, `Variant B: lambdarank`).

---

## 3. Honest Note on Data Scale Needed for ML Ranking

> [!IMPORTANT]
> **Production Threshold: Minimum 1,200 Completed Query Sessions**
> 
> Listwise and pairwise ranking algorithms (such as LambdaRank) adjust feature weights via gradients calculated across candidate permutations.
> - When interaction data is sparse ($<1,200$ completed sessions), gradient variance is excessively high.
> - In cold-start or low-density settings, ML rankers heavily overfit to commercial high-volume traders who accumulate clicks rapidly, while systematically down-ranking smallholders with fewer transactions.
> - **Platform Policy**: GrowCircle keeps transparent, verifiable rule-based matching as the default until at least 1,200 query sessions with feedback are recorded. Once the threshold is met, LambdaRank is enabled behind an A/B test flag with continuous fairness monitoring.

---

## 4. Fair Transport Rate Guide Regression

### Inputs & Cost Physics
- `distance_km`: One-way or multi-stop route kilometers.
- `load_weight_kg`: Total freight weight.
- `vehicle_type`:
  - `goods_auto` (<500 kg, mileage ~22 km/L, base ₹150)
  - `mini_truck` (500–1500 kg, mileage ~12 km/L, base ₹350)
  - `large_truck` (>1500 kg, mileage ~7 km/L, base ₹700)
- `fuel_price`: Diesel benchmark (₹98.50/L).
- `road_type`:
  - `national_highway`: 1.00
  - `state_highway`: 1.10
  - `district_road`: 1.25
  - `rural_unpaved`: 1.45 (45% roughness premium for wear and low average speed)
- `is_night`: Night operating surcharge (1.15 multiplier for 10 PM – 5 AM).

### Output Guarantee
- Never outputs a rigid point price. Returns:
  $$[R_{\min}, R_{\text{est}}, R_{\max}]$$
  with rate per kg and explicit disclaimer:
  *"Fair Transport Rate Guide (Indicative benchmark estimate). Actual freight charges are agreed directly between farmer/buyer and transporter."*

---

## 5. Google OR-Tools Multi-Stop CVRPTW Pooling Engine

### Constraints Solved:
1. **Vehicle Payload Capacity**: $\sum_{i \in \text{route}} \text{weight}_i \le \text{Capacity}_{\text{vehicle}}$
2. **Pickup Time Windows**: $\text{ready\_time}_i \le t_i \le \text{latest\_pickup}_i$
3. **Crop Spoilage Shelf-Life**:
   - Tomato: 18.0 hours
   - Banana: 36.0 hours
   - Papaya: 30.0 hours
   - Onion: 72.0 hours
   - Potato: 120.0 hours
   - $t_{\text{delivery}} \le \min_{i}(\text{ShelfLife}_i)$
4. **Road Distance Calibration**:
   - Rural road tortuosity factor: $1.28 \times \text{Haversine distance}$ (benchmarked on Andhra Pradesh village road networks).
5. **Reported Economic Impact**:
   - Consolidated vs separate single trips distance reduction (typically 40%–60% vehicle km saved).
   - Farmer cost-per-kg freight reduction (typically ₹0.60–₹0.95/kg saved, representing 35%–48% savings).

---

## 6. Driver Matching & Anti-Monopoly Fair Distribution

To prevent "super-drivers" from taking 100% of dispatch requests while nearby verified peers starve, we introduce an **equity dampening factor**:
$$F_{\text{equity}} = \exp\left(-\frac{\text{recent\_trips\_count}}{\tau}\right) \quad (\tau = 6.0)$$

$$\text{Final Score} = \text{BaseScore} \times \left(0.50 + 0.50 \cdot F_{\text{equity}}\right)$$

- Where $\text{BaseScore} = 0.35 \cdot \text{Proximity} + 0.25 \cdot \text{CapacityFit} + 0.20 \cdot \text{Rating} + 0.20 \cdot \text{Reliability}$.
- **Gini Coefficient Monitoring**: Measures trip distribution inequality among active verified drivers before and after fairness leveling.

---

## 7. Smallholder Fairness Audit & Parity Boost

- **Four-Fifths (80%) Disparate Impact Standard**:
  $$\text{Exposure Ratio} = \frac{\% \text{ Smallholders in Top-3}}{\% \text{ Smallholders in Pool}} \ge 0.80$$
- If $\text{Exposure Ratio} < 0.80$, an automatic fairness violation warning is triggered.
- **Parity Boost**: When enabled, the top-ranked qualified smallholder is promoted into the top-3 recommendations to preserve smallholder market access.
- **Audit Logging**: Every ranking decision is logged to an immutable structured decision log (`matching_audit_logs`) capturing request ID, timestamp, buyer ID, variant, and fairness audit metrics.

---

## 8. Verification & Performance Benchmarks

- **Test Coverage**: 146 / 146 unit & integration tests passing (`ml/tests/test_smart_matching.py`, `backend/tests/test_smart_matching_api.py`).
- **Linter Compliance**: 100% clean under `ruff check .`.
- **Validation Notebook**: `notebooks/ml5_logistics_pooling_savings.ipynb` with end-to-end demonstrations of pooling savings, rate curves, and anti-monopoly leveling.
