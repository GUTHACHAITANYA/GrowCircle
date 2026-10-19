# ADR 0005: Direct Selling, Verification, Matching Engine, and Masked Telephony Architecture

## Context
GrowCircle enables direct connections between smallholder farmers and verified bulk buyers (hostels, colleges, schools, hotels, retail shops, and supermarkets). To build a reliable trading ecosystem in India while maintaining regulatory compliance (DPDP Act) and trust, Phase 3 implements:
1. **Buyer & Institution Verification**: Verification of GST and Shop Act proofs stored encrypted at rest.
2. **Fresh Listing Quality Assurance**: Requiring fresh in-app camera captures (<24h, rejecting gallery uploads) and a mandatory 3-photo checklist (`whole_lot`, `close_up`, `opened_crate`) with plain Grade A/B/C descriptions.
3. **50 km Rule-Based Matching & Group Supply**: Proximity matching with scoring based on distance, quantity, grade, and farmer reliability, plus multi-farmer group supply aggregation for institutional tenders.
4. **Masked Telephony Bridge**: Connecting buyer and farmer without exposing personal phone numbers.
5. **Two-Way Negotiation & Read-Back Confirmation**: Counter-offer negotiation requiring explicit verbal or visual read-back confirmation before a binding deal is finalized.
6. **Zero Payment Custody**: GrowCircle acts purely as a connection and matching platform. No payments or escrow funds are collected; payment is settled directly upon physical delivery inspection using a secret 6-digit Handover OTP.

---

## Decisions

### 1. Data Schema & PostGIS Extension
- New PostgreSQL/PostGIS tables with foreign key integrity:
  - `buyers`: Registered commercial buyers, type, verification status (`pending`, `verified`, `rejected`), encrypted GSTIN, encrypted proof reference.
  - `buyer_needs`: Recurring weekly institutional demand specifications (crop, quantity, preferred grade, max price, frequency, PostGIS location).
  - `listings`: Farmer produce lots, quantity, expected price, harvest date, Grade A/B/C, fresh camera timestamp metadata, PostGIS location, and 3-photo checklist validation JSON.
  - `offers`: Bid / offer submissions between buyers and farmers, negotiation timeline, counter-offers, and status.
  - `deals`: Finalized agreements with agreed price, quantity, total value, secret Delivery OTP, and physical handover status.
  - `ratings`: Post-transaction two-way ratings (1-5 stars) and qualitative feedback.

### 2. DPDP Act Compliance & Proof Encryption at Rest
- Under the Digital Personal Data Protection (DPDP) Act of India, sensitive business tax IDs (GSTIN) and shop registration licenses must not be stored in plaintext.
- We utilize deterministic Fernet AES-256 encryption (`backend/app/services/security.py`) keyed from `SECRET_KEY`.
- Ciphertexts (`encrypted_gst_number`, `encrypted_document_ref`) are stored in PostgreSQL.
- Only authenticated administrators via `/market/admin/buyers/pending` with valid JWT tokens can decrypt and inspect documents in-memory for approval.

### 3. Media Freshness & Checklist Enforcement
- Fraud Prevention: Reject stale gallery photos or downloaded images.
  - The API requires `media_captured_at` metadata within the last 24 hours (`MAX_MEDIA_AGE_SECONDS = 86400`).
  - Stale timestamps (>24 hours) or future timestamps fail validation with HTTP 400.
- Mandatory 3-Photo Checklist:
  - Every listing must supply `whole_lot`, `close_up` (peel texture), and `opened_crate` (cross-section).
  - Grades are accompanied by clear, non-technical definitions:
    - **Grade A**: Uniform size, blemish-free skin, export/supermarket grade.
    - **Grade B**: Slight cosmetic marks, good firmness, kitchen/hostel grade.
    - **Grade C**: Variable size, fully ripe, processing grade.

### 4. Proximity Matching & Multi-Farmer Group Supply
- **Nearby Verified Buyers Ranking**:
  - Filter: Active verified buyers within 50 km (using Haversine and PostGIS `ST_Distance`).
  - Score Weights:
    - Distance: 40% (closer distance = higher score)
    - Quantity fit: 25% (closer match to required volume)
    - Grade match: 15% (exact preferred grade match)
    - Reliability: 20% (historical completion score)
- **Group Supply Aggregator**:
  - Institutions often need multi-tonne quantities (e.g., 2,000 kg/week) that single smallholders cannot fulfill alone.
  - Algorithm greedily bundles nearby farmer listings within 50 km until the target volume is met, computing the combined volume and weighted average price per kg for a consolidated procurement trip.

### 5. Masked Telephony Provider Interface
- Added `initiate_masked_call(caller_phone, callee_phone, context_id)` to `TelephonyProvider`.
- Virtual bridge bridges both parties using a virtual DID number (e.g. via Exotel Virtual Number or Twilio Proxy) without revealing either farmer or buyer private mobile numbers.

### 6. Read-Back Confirmation & Secret Delivery OTP
- Before any counter-offer acceptance or deal creation:
  - The web application and voice IVR enforce an explicit **Read-Back Confirmation**:
    *"You are agreeing to purchase [X] kg of [Variety] [Crop] at ₹[Y]/kg (Total ₹[Z]) from Farmer [Name]. Payment is settled directly upon physical delivery."*
  - Requires explicit affirmative confirmation before the deal record is created.
- A 6-digit Secret Delivery OTP is generated. The buyer inspects crate quality upon physical arrival at the kitchen/dock and shares the OTP with the farmer/driver to authorize completion.

### 7. Zero Payment Custody Policy
- GrowCircle does not act as a payment aggregator, payment gateway, or escrow custodian.
- This eliminates RBI Payment Aggregator licensing requirements and banking custody overhead, ensuring 100% legal compliance and transparency.

---

## Consequences
- Farmers can sell directly to nearby colleges, hotels, and hostels without intermediaries taking 20-30% cuts.
- Institutions gain access to fresh produce verified within 24 hours of harvest with complete traceability.
- Buyer documents remain securely encrypted under DPDP Act standards.
- Platform is completely testable offline with mock providers and passes all unit, integration, and browser tests.
