# Real-World Data Gaps Requiring Farmer Input & Crowdsourcing

**Phase**: ML-3 Agro-Climatic Intelligence  
**Document Purpose**: Identifies critical structural data blindspots in public government datasets and outlines participatory crowdsourcing mechanisms through GrowCircle's Farm Diary, IVR, and WhatsApp channels.

---

## Executive Context
The GrowCircle Phase ML-3 engine integrates official government price history (Agmarknet), district area statistics (Directorate of Economics & Statistics AP), and credit norms (SLBC AP Scale of Finance). While these establish a reliable scientific baseline, **government datasets suffer from significant reporting latency (often 60–180 days post-season) and coarse geographic aggregation**.

To transition from macro-district guidance to hyper-local village precision and eliminate "false alarm" weather blindspots, the following 6 structural data gaps require real farmer inputs.

---

## 1. Real-Time Pre-Planting Sowing Intentions
- **The Government Gap**:
  - Official district acreage statistics compiled by DES and revenue patwaris are finalized 2 to 4 months *after* transplantation when field inspections conclude.
  - By the time government reports confirm that Tomato acreage expanded by 25% in Annamayya district, the seeds are in the ground and the harvest glut is locked in.
- **Farmer Input Needed**:
  - Intended crop and proposed acreage 30 days prior to field planting.
- **GrowCircle Collection Mechanism**:
  - One-tap WhatsApp button poll & automated 30-second IVR outbound call to registered farmers in May (Kharif) and October (Rabi):
    > *"Which crop are you preparing your plot for this coming month: [1] Tomato [2] Onion [3] Chilli [4] Maize [5] Banana?"*
  - Feeds directly into a dynamic `village_intent_crowding_index`.

---

## 2. Commercial Nursery Seedling Bookings
- **The Government Gap**:
  - Most commercial horticulture in Andhra Pradesh (Tomato, Chilli, Brinjal) no longer uses direct seed broadcasting; farmers purchase 21–28 day plug seedlings from private commercial shade-net nurseries.
  - Government agricultural data tracks certified seed sales, but does not capture private nursery seedling production volumes.
- **Farmer Input Needed**:
  - Quantity of seedling trays ordered and expected nursery delivery week.
- **GrowCircle Collection Mechanism**:
  - Seedling purchase photo upload or voice diary entry in Farm Diary:
    > *"Ordered 15,000 hybrid chilli seedlings from Lam nursery for delivery on July 10th."*

---

## 3. Micro-Irrigation & Borewell Discharge Health
- **The Government Gap**:
  - SLBC cost-of-cultivation norms assume standard irrigation availability.
  - In drought-prone districts like Anantapur, Kurnool, and Annamayya, borewell discharge drops precipitously during dry spells, cutting actual harvest yields by 40–60% below official norms ($y_{10}$ disaster scenario).
- **Farmer Input Needed**:
  - Source of water: Canal, open well, borewell, or rainfed.
  - Current borewell pump running duration (e.g. continuous 6 hours vs struggling 1.5 hours/day).
- **GrowCircle Collection Mechanism**:
  - Plot profile setup in Farm Diary (`water_source` and `borewell_health_status`).

---

## 4. Specific Hybrid Variety Genetics & Pest Resistance
- **The Government Gap**:
  - Public datasets aggregate all varieties into a generic commodity category (e.g. "Chilli" or "Tomato").
  - In practice, planting a virus-susceptible variety during a whitefly epidemic yields complete crop failure, whereas planting a resistant hybrid (e.g. *Arka Rakshak* for Tomato, *LCA 334* for Chilli) yields standard harvest volumes.
  - Seed costs vary from ₹800/acre for open-pollinated seeds to ₹14,000/acre for proprietary hybrid seeds.
- **Farmer Input Needed**:
  - Exact seed variety or hybrid brand name purchased.
- **GrowCircle Collection Mechanism**:
  - Voice entry transcription in Farm Diary:
    > *"Bought 5 packets of US 440 tomato seeds for 6,000 rupees."*

---

## 5. Farm-Gate Distress Sales & Intermediary Broker Exploitation
- **The Government Gap**:
  - Agmarknet publishes modal prices from regulated APMC market yards.
  - Smallholder farmers who cannot afford transport to the mandi often sell at their farm-gate to village commission agents (*dalals* or *vyaparis*) at 20–35% discounts below official mandi rates.
  - These distress transactions never appear in official records, artificially inflating official price reporting.
- **Farmer Input Needed**:
  - Actual farm-gate transaction price, deductions (commission/weighment charges), and payment receipt terms.
- **GrowCircle Collection Mechanism**:
  - Farm Diary `sale_revenue` entries. GrowCircle automatically compares the farmer's net sale realization with the mandi average on that date to calculate the true broker spread.

---

## 6. On-Farm & Private Cold Storage Booking Status
- **The Government Gap**:
  - For semi-perishable crops (Onion, Dry Chilli, Potato, Turmeric), market supply depends not just on harvest volume, but on the proportion of crop entering cold storage versus dumped directly onto the spot market.
  - State warehouse corporation data covers public godowns, but over 70% of cold storage capacity in Guntur and Rayalaseema is privately held.
- **Farmer Input Needed**:
  - Did the farmer store produce in cold storage (and holding duration), or sell immediately off the field?
- **GrowCircle Collection Mechanism**:
  - Post-harvest prompt in Farm Diary: *"Harvest completed. Produce stored in cold room or sold at mandi?"*

---

## Summary & Incentive Strategy for Farmers

| Data Gap | Priority | Incentive for Farmer |
| :--- | :--- | :--- |
| **Sowing Intentions** | **CRITICAL** | Instant localized crowding alert warning them if their village is over-planting |
| **Nursery Bookings** | **HIGH** | Accurate nursery price comparison across nearby mandals |
| **Water / Borewell Health** | **HIGH** | Calibrated irrigation scheduling advice via WhatsApp |
| **Variety Genetics** | **MEDIUM** | Real yield comparison vs other farmers planting the same hybrid |
| **Farm-Gate Distress Sales** | **HIGH** | Connection to verified GrowCircle institutional buyers willing to pick up at farm |
| **Cold Storage Utilization** | **MEDIUM** | Guide rate for local cold storage rental and seasonal price spike alerts |
