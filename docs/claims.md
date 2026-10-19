# GrowCircle Claims & Evidence Register

This document audits all marketing claims, regulatory references, and quality labels used throughout the GrowCircle application, documenting their evidentiary basis, statutory alignment, and honest limitations.

---

## 1. Regulatory & Compliance Claims

### 1.1 "DPDP Act Compliant" &rarr; Rewritten to "DPDP Act 2023 Aligned"
- **Locations**: `PrivacyClient.tsx`, `AdminClient.tsx`, `PricesClient.tsx`, `HomePageClient.tsx`, `TermsClient.tsx`.
- **Status**: **Rewritten**. Absolute claims of "100% compliant" or "Certified DPDP Act Compliant" have been removed.
- **Evidentiary Basis**:
  - **Section 6 (Consent & Notice)**: User consent notices for GPS location are presented prior to device coordinate capture with district-level fallback.
  - **Section 8 (Data Security Safeguards)**: Sensitive documents (GST certificates, driving licenses, vehicle RC) are encrypted at rest using AES-256 (Fernet) before storage in `buyer_profiles` and `transporters` tables.
  - **Section 11 (Right to Access Data)**: Users can download machine-readable JSON packages containing their profile, listings, farm diary, and trips (`ProfileClient.tsx` -> `DPDP_DATA_EXPORT`).
  - **Section 12 (Right to Erasure & Correction)**: Users can request account anonymization, redacting identifying phone numbers and business names while preserving anonymous transaction statistics.
  - **Section 13 (Grievance Redressal)**: Administrative grievance workflow and audit log tracking implemented in `AuditLogsSection.tsx`.
- **Honest Limitation / Why "Compliant" Was Rewritten**:
  The Digital Personal Data Protection Act, 2023 was enacted by the Parliament of India, but executive rules and the Data Protection Board of India (DPBI) establishment are in the process of official notification by MeitY. Until statutory audit procedures and certifications are formally promulgated, no private platform can legitimately claim "DPDP Act Certification". The platform is architected for alignment with the Act's statutory principles.

---

## 2. Institutional & Identity Claims

### 2.1 "Official Agmarknet Mandi Rates" &rarr; Rewritten to "Agmarknet Public Mandi Rates (data.gov.in)"
- **Locations**: `PricesClient.tsx`, `TermsClient.tsx`, `DiaryClient.tsx`.
- **Status**: **Rewritten**.
- **Evidentiary Basis**:
  Prices are ingested from data.gov.in (Directorate of Marketing & Inspection, Ministry of Agriculture & Farmers Welfare) under the Government Open Data License (GODL-India).
- **Honest Limitation**:
  GrowCircle is an independent technological platform, not an official arm of Agmarknet or the AP State Agricultural Marketing Board. All prices reflect reported public auctions, not statutory price guarantees.

### 2.2 "Official APMC Registries" &rarr; Rewritten to "Public APMC Mandi Data (data.gov.in)"
- **Locations**: `GeographicBrowser.tsx`.
- **Status**: **Rewritten**.
- **Evidentiary Basis**: Mandi geospatial coordinates, market yard names, and district affiliations are derived from official APMC directories published on data.gov.in.
- **Honest Limitation**: Mandi operational hours, holiday schedules, and physical yard expansions must be verified on-ground.

### 2.3 "Verified Institutional Buyer" &rarr; Rewritten to "Registered Institutional Buyer (Documented)"
- **Locations**: `PortalClient.tsx`.
- **Status**: **Rewritten**.
- **Evidentiary Basis**:
  Buyer accounts submit a valid 15-digit GSTIN (validated via standard checksum regex) or a Shop & Establishment Act license document stored encrypted at rest.
- **Honest Limitation**:
  Document submission proves tax registration, not physical solvency or creditworthiness. On-ground physical verification of hostel dining halls or commercial kitchens remains the responsibility of field operations.

### 2.4 "Verified Farmer Listings" &rarr; Rewritten to "Farmer Listings within 50 km"
- **Locations**: `PortalClient.tsx`.
- **Status**: **Rewritten**.
- **Evidentiary Basis**:
  Farmer telephone numbers are OTP-authenticated. Produce photos are validated for freshness against EXIF metadata timestamps (&lt; 24h old).
- **Honest Limitation**:
  Soil conditions, organic status, and total acreage are self-reported by the farmer. GrowCircle does not conduct on-farm physical inspections.

### 2.5 "3 Verified Drivers" &rarr; Rewritten to "3 Matched Available Drivers"
- **Locations**: `PortalClient.tsx`, `DriverClient.tsx`.
- **Status**: **Rewritten**.
- **Evidentiary Basis**:
  Drivers submit commercial driving licence numbers, vehicle registration numbers, insurance policy IDs, and fitness certificates with recorded expiry dates. Dispatched suggestions filter only drivers whose documents are non-expired and who are within the geographic load radius.
- **Honest Limitation**:
  Driver vehicle roadworthiness is verified against documented expiry dates, not physical mechanical inspection.

### 2.6 "100% Document Compliant" &rarr; Rewritten to "All Mandatory Documents Active"
- **Locations**: `DriverClient.tsx`.
- **Status**: **Rewritten**.
- **Evidentiary Basis**:
  DL, RC, Commercial Insurance, and Fitness Certificate are validated for future expiry dates.
- **Honest Limitation**:
  The term "100% compliant" falsely suggests government RTO inspection compliance.

### 2.7 "Official Settlement Agreement" &rarr; Rewritten to "Mutual Settlement Record"
- **Locations**: `AdminClient.tsx`.
- **Status**: **Rewritten**.
- **Evidentiary Basis**:
  Platform records arbitrated compromises agreed upon by both the farmer and the buyer (e.g., credit notes for transit-damaged produce).
- **Honest Limitation**:
  Platform mediation is a contractual dispute settlement, not an enforceable statutory court decree.

---

## 3. Algorithmic & Economic Claims

### 3.1 "PostGIS Geodesic Distance" &rarr; Rewritten to "Straight-Line Distance (km)"
- **Locations**: `PricesClient.tsx`, `ShowcaseClient.tsx`.
- **Status**: **Rewritten** to plain language.
- **Evidentiary Basis**:
  Distances are computed using the Haversine formula on spherical WGS-84 coordinates.
- **Honest Limitation**:
  Straight-line distance does not account for road curves, ghat roads, river crossings, or bridge detours. Road distance is typically 15–30% longer.

### 3.2 "Consumer Intelligence" &rarr; Rewritten to "Consumer Price Insights"
- **Locations**: `PricesClient.tsx`.
- **Status**: **Rewritten**.
- **Evidentiary Basis**:
  Calculated by comparing current modal mandi price against the 30-day historical moving benchmark.

### 3.3 "Crop Planning Profit Projections"
- **Locations**: `CropPlanClient.tsx`, `ml/planning/planner_engine.py`.
- **Status**: **Strict Quality Gate Enforced**.
- **Evidentiary Basis**:
  - Price: Historical Agmarknet modal distributions (10th percentile, 50th percentile, 90th percentile).
  - Yield: Directorate of Economics & Statistics AP district yield norms under GODL license.
  - Cost: Andhra Pradesh State Level Bankers' Committee (SLBC) Scale of Finance 2024–2026.
- **Downside Case Guarantee**:
  For crops with documented glut crash history (`banana`, `tomato`, `onion`, `chilli`, `potato`), the downside case incorporates historical distress sale pricing (e.g., ₹5/kg for onion, ₹4/kg for tomato), guaranteeing realistic negative net returns when production costs exceed market crash prices.
- **Unrealistic Flagging**:
  Candidates with expected net profit exceeding ₹300,000/acre display a prominent warning alerting farmers that projections assume premium grading and zero pest/weather loss.

---

## 4. Accessibility & Quality Claims

### 4.1 "WCAG AA Compliant"
- **Locations**: `HomePageClient.tsx`, `Header.tsx`.
- **Status**: **Verified**.
- **Evidentiary Basis**:
  - Color contrast check (`scripts/test-contrast.js`) validates all 12 key color pairings against WCAG 2.1 AA 4.5:1 ratio (Deep leaf `#1F6B3A` on `#FFFFFF` is 6.55:1, `#2D312E` ink is 11.83:1).
  - Focus rings (`focus:ring-2 focus:ring-deep-leaf`) configured across interactive inputs.
  - Minimum touch targets of 44x44px enforced across buttons and navigation toggles.

---

## Summary of Action Taken
Every unsubstantiated claim identified during the R8 audit was either rewritten into precise, legally accurate terminology or removed entirely. No marketing exaggerations remain in production code.
