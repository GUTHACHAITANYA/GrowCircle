# ADR 0006: Transport Matching, Expiry Enforcement, Indicative Guide Rates, and Freight Pooling v1

## Context
Following the completion of direct selling and deal confirmation (Phase 3), the critical physical link in the agricultural supply chain is transport. In rural and peri-urban India, smallholder farmers and local institutions face high logistical friction:
1. **Unregulated or Unverified Vehicles**: Absence of document compliance verification (driving licence, fitness certificate, insurance, registration).
2. **Sub-optimal Vehicle Allocation**: Assigning a 3-tonne truck for a 300 kg banana load or an auto for a 2-tonne load leads to wasted capacity or vehicle breakdowns.
3. **Price Opacity**: Lack of transparent benchmark freight rates leads to arbitrary overcharging.
4. **Empty Return Runs & High Small-Load Costs**: Fragmented nearby farmers sending small loads independently to the same city institution multiply transport costs.
5. **Transit Damage & Delivery Disputes**: Lack of verification protocols leads to unresolvable disputes when produce is bruised in transit.

GrowCircle Phase 4 addresses these challenges with an integrated transport engine, rule-based pooling, mobile-first driver flows (Web/PWA & WhatsApp), and administrative arbitration.

---

## Decisions

### 1. Transporter Compliance & Automatic Document Expiry Lock
- All transporters maintain records for:
  - Driving Licence (number, expiry date, photo)
  - Vehicle Registration Certificate (RC number, expiry date, copy)
  - Commercial Vehicle Insurance (policy number, expiry date, certificate)
  - Vehicle Fitness Certificate (FC number, expiry date, certificate)
  - Vehicle Type (`goods_auto`, `mini_truck`, `large_truck`), payload capacity (kg), and service area.
- **Strict Compliance Enforcement**:
  - `is_active_and_compliant()` automatically checks whether *any* of the 4 document expiry dates are `< date.today()`.
  - Transporters with any expired documents are **immediately and automatically hidden** from dispatch ranking algorithms and load assignment.
  - The driver interface displays a red compliance lock banner, and the availability toggle is locked until renewals are uploaded and verified by an administrator.

### 2. Post-Deal Matching Engine (Top 3 Verified Drivers)
- Upon deal confirmation, the system matches the load to verified, active, compliant drivers near the pickup farm gate.
- **Weight Classification Rules**:
  - **Load < 500 kg**: `goods_auto` (e.g. Piaggio Ape, Bajaj Maxima)
  - **Load 500 kg to 1,500 kg**: `mini_truck` (e.g. Tata Ace Gold, Mahindra Bolero Maxi Truck)
  - **Load > 1,500 kg**: `large_truck` (e.g. Ashok Leyland Dost+, Eicher Pro)
- **Ranking**:
  - Filters strictly for active (`is_available_today = True`), admin-verified, and document-compliant drivers within the pickup district/radius.
  - Ranks by Haversine proximity from driver base to pickup location.
  - Returns exactly the top 3 candidate drivers.

### 3. Transparent Indicative Guide Rates
- GrowCircle maintains **zero payment custody** and does not act as a tariff cartel. Freight is agreed directly between transporter and parties.
- The platform provides a clear **Guide Rate Formula**:
  - `goods_auto`: ₹150 base fare + ₹18 per km
  - `mini_truck`: ₹350 base fare + ₹25 per km
  - `large_truck`: ₹700 base fare + ₹38 per km
  - Minimum billable distance: 2 km.
- **Mandatory Disclaimer**:
  - Every UI and API response clearly states:
    > *"Guide rate only (indicative estimate). Calculated based on distance and vehicle type. Transporter and farmer/buyer agree directly on final freight charges."*

### 4. Trip Lifecycle, OTP Handshake & Dispute Handling
- Trip status progression:
  - `assigned` &rarr; `arrived_pickup` &rarr; `in_transit` &rarr; `delivered` (or `disputed`).
- **Cryptographic OTP Handshake**:
  - **Pickup OTP** (4-digit, generated for farmer): Driver enters this upon inspecting crates at the farm gate to start transit (`assigned` &rarr; `in_transit`).
  - **Delivery OTP** (6-digit, generated for buyer): Driver enters this upon physical crate inspection by buyer to finalize delivery (`in_transit` &rarr; `delivered`).
- **Delivery Dispute Arbitration**:
  - If produce is damaged or bruised during transport, the buyer can file a dispute before OTP release.
  - **Mandatory Photographic Proof**: Buyers must capture and submit photographic evidence of damaged crates taken at the delivery gate (`buyer_dispute_photo_url`). Empty or missing photos are rejected with HTTP 422.
  - Disputed trips are routed to the Admin Dispute Queue, where platform administrators review the damage photo, notes, and guide rate to record settlement agreements.

### 5. Freight Pooling v1 (Rule-Based Engine)
- To reduce freight costs for smallholders and maximize truck utilization:
  - The algorithm identifies active loads within a **15 km pickup cluster** going to the **same destination institution** (e.g. hostel or college).
  - Bundles loads if total weight is &le; vehicle capacity.
  - Computes single 3-stop route (Pickup A &rarr; Pickup B &rarr; Dropoff) and calculates combined freight savings (typically 18-25% savings for farmers, higher hourly earnings for drivers).

### 6. Driver Mobile-First Experience & WhatsApp Door
- **Web / PWA Portal (`/[locale]/driver`)**:
  - Large touch targets (&ge;44px), WCAG AA color contrast, responsive layout.
  - Available Today toggle switch.
  - Real-time Document Expiry Radar with test simulator.
  - Active Trip dashboard with masked call links and OTP inputs.
  - Two-way mutual ratings (1-5 stars) for farmer and buyer.
- **WhatsApp Webhook Integration**:
  - Drivers can interact entirely via SMS/WhatsApp text & voice notes without app downloads:
    - `AVAILABLE YES` / `AVAILABLE NO`
    - `PICKUP <otp>`
    - `DELIVER <otp>`
    - `TRIPS`

---

## Consequences
- Farmers and buyers get rapid, load-appropriate transport without arbitrary price gouging.
- Drivers with expired documentation cannot operate on the platform, significantly elevating transport safety and reliability.
- Rule-based pooling v1 reduces empty return trips and aggregate carbon emissions.
- Zero payment custody ensures GrowCircle remains an open, regulatory-clean utility matching platform.
