# GrowCircle Phase 4: Transport System Documentation

Phase 4 introduces verified agricultural transport logistics connecting farmers, buyers, and transporters across Andhra Pradesh.

---

## 1. Core Capabilities

1. **Transporter Registry & Document Compliance**:
   - Verification of Driving Licence, Registration Certificate (RC), Commercial Vehicle Insurance, and Vehicle Fitness Certificate.
   - **Automatic Expiry Checks**: Drivers with any expired document are strictly and automatically hidden from load dispatch algorithms.
   - **Available Today** real-time toggle.

2. **Load-Matched 3-Driver Dispatch**:
   - Automatically triggered upon deal finalization.
   - Categorizes loads:
     - `< 500 kg`: `goods_auto` (e.g. Piaggio Ape, Bajaj Maxima)
     - `500 kg - 1.5 t`: `mini_truck` (e.g. Tata Ace Gold, Mahindra Bolero Maxi)
     - `> 1.5 t`: `large_truck` (e.g. Ashok Leyland Dost+, Eicher Pro)
   - Ranks active, verified, compliant drivers near the pickup farm gate and returns top 3.

3. **Indicative Guide Rate Engine**:
   - Formula: `base_fare + (distance_km * per_km_rate)`
   - Clearly labeled in all interfaces as an indicative guide, not a fixed tariff. Zero payment custody.

4. **Trip Lifecycle & Dual OTP Handshake**:
   - `assigned` &rarr; `in_transit` via 4-digit **Pickup OTP** at farm gate.
   - `in_transit` &rarr; `delivered` via 6-digit **Delivery OTP** at buyer delivery gate.
   - **Dispute Flow**: Buyer can file complaint with mandatory delivery damage photo proof, withholding OTP until Admin arbitration.
   - **Mutual Ratings**: Two-way 1-5 star ratings for farmer, driver, and buyer.

5. **Freight Pooling v1 (Rule-Based)**:
   - Groups nearby farm pickups within 15 km going to the same institutional buyer into a single multi-stop trip with calculated freight savings.

6. **Mobile-First Driver Flow (Web/PWA & WhatsApp)**:
   - Responsive web portal at `/[locale]/driver`.
   - Full driver flow via WhatsApp text commands (`AVAILABLE YES/NO`, `PICKUP <otp>`, `DELIVER <otp>`, `TRIPS`).

7. **Admin Verification & Dispute Arbitration**:
   - Transporters Queue for inspecting vehicle credentials, expiry dates, and document photos.
   - Delivery Disputes Queue for viewing crate damage photos, inspecting complaints, and recording settlement terms.

---

## 2. API Reference (`/transport`)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/transport/transporters` | Register a new transporter with vehicle credentials and document expiry dates |
| `GET` | `/transport/transporters/{id}` | Retrieve transporter profile, compliance status, and document validity |
| `PATCH` | `/transport/transporters/{id}/availability` | Toggle `is_available_today` status |
| `GET` | `/transport/matches/suggest` | Suggest top 3 active, verified, compliant drivers near pickup point matched to load weight |
| `GET` | `/transport/pooling/plan` | Identify rule-based pooled multi-farm trips within 15 km cluster for same destination |
| `POST` | `/transport/trips` | Create trip assignment from confirmed deal with guide rate and OTPs |
| `GET` | `/transport/trips/{id}` | Get trip status, route, and OTP details |
| `POST` | `/transport/trips/{id}/verify-pickup` | Verify 4-digit Pickup OTP and advance status to `in_transit` |
| `POST` | `/transport/trips/{id}/verify-delivery` | Verify 6-digit Delivery OTP and mark `delivered` |
| `POST` | `/transport/trips/{id}/dispute` | Buyer raises delivery dispute requiring mandatory damage photo proof |
| `POST` | `/transport/trips/{id}/resolve-dispute` | Admin records dispute settlement agreement |
| `POST` | `/transport/trips/{id}/ratings` | Submit mutual trip rating (driver &harr; farmer &harr; buyer) |

---

## 3. WhatsApp Integration Reference

Drivers can execute all operations by messaging GrowCircle's WhatsApp webhook:
- `AVAILABLE YES` / `AVAILABLE NO`: Toggle availability
- `PICKUP 8291`: Confirm farm gate crate loading
- `DELIVER 492018`: Confirm buyer crate handover
- `TRIPS`: View assigned trips and guide fares

---

## 4. Test Verification Summary

- **Backend Pytest**: 63 / 63 tests passing (100% pass rate in 3.30s).
- **Frontend Typecheck**: TypeScript strict mode passing with 0 errors.
- **Frontend Linter**: ESLint passing with 0 warnings.
- **Accessibility**: Jest WCAG AA color contrast suite passing 12/12 checks.
- **End-to-End Browser Verification**: Tested via `browser_subagent` covering:
  - Driver portal (`/en/driver`): Availability toggle, document expiry simulation with compliance lock, freight pooling v1 acceptance, and OTP verification lifecycle.
  - Admin view (`/en/admin`): Transporter verification queue, expired document detection, driver approval, and delivery dispute resolution.
  - Buyer portal (`/en/portal`): Matched 3-driver suggestion with indicative guide rates, driver assignment, and delivery dispute submission with photo proof.
