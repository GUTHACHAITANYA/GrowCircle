# ADR 0004: IVR Telephony, WhatsApp Cloud API, and Multilingual Speech Architecture

## Context
GrowCircle is a voice-first platform connecting farmers, buyers, transport drivers, and everyday consumers in India. Because many farmers have limited literacy and feature phones (non-smartphones), access cannot rely exclusively on web or app interfaces.

In Phase 2, we implement:
1. **Phone Call (IVR) Door**: Missed call callback flow with DTMF keypad menus and spoken mandi prices.
2. **WhatsApp Cloud API Door**: Conversational interface handling voice notes, GPS location sharing, and 7 AM automated daily price alerts.
3. **Multilingual Speech Layer**: Speech-to-Text (STT) and Text-to-Speech (TTS) supporting Telugu, Hindi, Gujarati, and English with audio caching and fallback across Indian AI providers (Bhashini, Sarvam AI, Google Cloud).
4. Reusing Phase 1 price and geospatial database engine exclusively without data duplication.

## Decisions

### 1. Unified Backend Reuse ("One Engine, Multiple Doors")
- IVR and WhatsApp handlers act strictly as translation adapters:
  - They invoke the existing Phase 1 `GeoService.get_nearby_mandis()` and `Price` models.
  - No separate price query logic or duplicate tables are introduced.

### 2. Telephony Provider Abstraction & Missed Call Flow
- `TelephonyProvider` abstract interface isolates provider specifics.
- Implementations: `MockTelephonyProvider` (for deterministic offline testing), `ExotelTelephonyProvider` (for Indian DLT / PRI / SIP trunks), and `TwilioTelephonyProvider`.
- Flow:
  1. User calls number, call drops (`/ivr/missed-call`).
  2. Outbound callback triggered immediately.
  3. When answered (`/ivr/callback`), user profile is checked:
     - Missing language -> DTMF 1=Telugu, 2=Hindi, 3=Gujarati (`/ivr/language-selection`).
     - Missing district -> DTMF 1=Guntur, 2=NTR, 3=Tirupati, 4=Kurnool (`/ivr/district-selection`).
     - Both saved -> "Welcome to GrowCircle" in saved language -> Crop Menu (`/ivr/crop-menu`).
  4. Speaks 3 nearest mandis' modal prices and distances under 1 minute.
  5. Post-answer menu: "Press 1 to sell, 2 for transport, 9 to repeat" (`/ivr/action-selection`). Choices 1 and 2 write to the `inquiries` table as actionable leads; choice 9 replays prices.

### 3. Speech AI (STT / TTS) Architecture
- Multi-provider adapter chain with automatic fallback:
  - Primary provider (configurable via `STT_PROVIDER` / `TTS_PROVIDER`).
  - Fallbacks: Sarvam AI -> Bhashini -> Google Cloud -> Deterministic Mock.
- **Audio Caching**:
  - Daily spoken price announcements are cached per `sha256(crop_id + district + date + language + unit)`.
  - Avoids redundant synthesis costs.
- **Pronunciation & Concatenation**:
  - `backend/app/services/speech/pronunciation.py` maintains phonetic translations for all crops and mandis across Telugu, Hindi, Gujarati, and English.
  - Static common phrases are pre-recorded or synthesized once; dynamic synthesis is used for numbers, dates, and localized names.

### 4. WhatsApp Cloud API Webhook & Daily 7 AM Broadcast
- Inbound dispatcher (`/whatsapp/webhook`):
  - **Voice Notes**: Transcribes audio -> extracts crop/district entities -> queries Phase 1 price engine -> replies with both formatted text and audio voice note.
  - **Location Sharing**: Extracts coordinates -> queries PostGIS `ST_Distance` -> replies with 3 nearest mandis.
  - **Text Queries**: Parses queries ("banana price in guntur") -> returns price summary.
- **7 AM Daily Broadcast**:
  - Scheduled Celery beat task (`broadcast_daily_whatsapp_prices`) at 07:00 IST (01:30 UTC).
  - Delivers approved Meta Utility message templates (`daily_mandi_price_alert`) exclusively to users with explicit DPDP Act consent (`consent_at`).

## Consequences
- Farmers can access real prices via free missed calls without smartphones or internet connectivity.
- Smartphone users can communicate naturally via WhatsApp voice notes in their mother tongue.
- Zero mock data in production; full end-to-end flow is testable locally without live telecom or Meta credentials.
