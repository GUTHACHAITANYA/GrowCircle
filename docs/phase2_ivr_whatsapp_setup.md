# Phase 2: IVR Telephony, WhatsApp Cloud API & Sandbox Run Guide

## Overview
GrowCircle Phase 2 adds two conversational voice-first doors to the Phase 1 core engine:
1. **Phone Call (IVR)**: Missed call callback flow with DTMF keypad menus, spoken prices under 1 minute, and post-answer lead recording (Sell / Transport / Repeat).
2. **WhatsApp Cloud API**: Voice note input with text + voice note reply, location sharing with nearest mandis, and an automated 7:00 AM IST daily broadcast.
3. **Multilingual Speech Layer**: STT and TTS supporting Telugu, Hindi, Gujarati, and English with audio caching and multi-provider fallbacks (Bhashini, Sarvam AI, Google Cloud, and Mock).

All Phase 2 features reuse the Phase 1 database and PostGIS spatial engine directly without data duplication.

---

## Part 1: Production Setup Checklist (What You Must Configure)

When transitioning from the local mock sandbox to live production with real Indian telephone carriers and Meta, you must complete the following regulatory and account registrations.

### 1. Indian Virtual Phone Number & Cloud Telephony (Exotel / Twilio / Tata Tele)
To receive missed calls and trigger automated callbacks to Indian mobile numbers:
- **Provider Account**: Register with an Indian cloud telephony provider like **Exotel** (`exotel.com`), **Knowlarity**, or **Tata Tele Business Services**. (Twilio is also supported for international/SIP setups).
- **Virtual Number (DID)**: Purchase an Indian 10-digit mobile/landline virtual number or toll-free number (1800-series).
- **Corporate KYC Documentation Required**:
  1. Certificate of Incorporation (MCA) / Business Registration Certificate.
  2. Entity PAN Card.
  3. Goods and Services Tax (GST) Certificate.
  4. Authorized Signatory ID Proof (Aadhaar / Passport) and Address Proof.
  5. Letter of Authorization on company letterhead authorizing the account administrator.
- **Webhook Configuration**:
  - In your provider dashboard, configure the incoming call webhook to point to:
    `POST https://api.growcircle.in/ivr/missed-call`
  - Callback action URL:
    `POST https://api.growcircle.in/ivr/callback`

---

### 2. TRAI Telecom Commercial Communications Regulations (DLT Compliance)
Under Telecom Regulatory Authority of India (TRAI) TCCCPR 2018 regulations, all transactional and service automated calls and SMS in India must be registered on a Distributed Ledger Technology (DLT) platform:
- **DLT Portals**: Register as a **Principal Entity (PE)** on any telecom operator's DLT portal (e.g., Vilpower / Vodafone-Idea, Jio DLT, Airtel DLT, or BSNL DLT).
- **Steps**:
  1. **Principal Entity Registration**: Submit company PAN, GST, and incorporation proof. Once approved, you will receive a unique **PE-ID** (19-digit number).
  2. **Header (Sender ID) Registration**: Register your 6-character alpha header (e.g., `GRWCRL` or `GRWCIR`) under the **Transactional / Service Explicit** category.
  3. **Content Template Registration**: Submit pre-approved voice blast and SMS consent templates. Note the assigned **Template ID**.

---

### 3. Meta WhatsApp Business Account (WABA) & Cloud API
To enable the official WhatsApp bot door:
- **Meta Business Manager**:
  1. Create or log in to [business.facebook.com](https://business.facebook.com).
  2. Complete **Business Verification** by submitting business registration documents and an official utility bill or bank statement showing the exact legal business name and address.
- **WhatsApp Cloud API Onboarding**:
  1. In the Meta App Developer Dashboard, add the **WhatsApp** product.
  2. Register a dedicated phone number (this number cannot be currently active on personal WhatsApp or the WhatsApp Business mobile app).
  3. Verify ownership via OTP / phone call.
  4. Submit **Display Name** for approval: `"GrowCircle"`. Ensure your website and business documentation clearly reflect the GrowCircle brand name.
  5. Set the profile picture using `assets/brand/logo-mark.svg` (or generated 512x512 PNG).
- **Webhook Subscription**:
  - Webhook URL: `https://api.growcircle.in/whatsapp/webhook`
  - Verify Token: Matches `WHATSAPP_VERIFY_TOKEN` in `.env`
  - Subscribed Fields: Check `messages`.
- **Approved Message Template**:
  Submit the utility template in WhatsApp Manager:
  - **Template Name**: `daily_mandi_price_alert`
  - **Category**: `UTILITY`
  - **Header**: Image (GrowCircle logo)
  - **Body**:
    ```
    GrowCircle: Today's mandi price update for {{1}} in {{2}}.
    Top Modal Price: {{3}}
    Key Mandis: {{4}}
    Date: {{5}}
    Reply with SELL or TRANSPORT to connect with verified partners.
    ```
  - **Languages**: Telugu (`te`), Hindi (`hi`), Gujarati (`gu`), English (`en`).

---

### 4. Indian AI Speech Platforms (STT & TTS)
- **MeitY Bhashini (National Language Translation Mission)**:
  - Create an account on the ULCA portal: `bhashini.gov.in/ulca`
  - Generate your `user_id`, `ulcaApiKey`, and `pipeline_id`.
  - Set `BHASHINI_USER_ID`, `BHASHINI_API_KEY`, and `BHASHINI_PIPELINE_ID` in `.env`.
- **Sarvam AI**:
  - Sign up at `dashboard.sarvam.ai`.
  - Generate an API key.
  - Set `SARVAM_API_KEY` in `.env`. Provides `saaras:v1` for STT and `bulbul:v1` for TTS.
- **Google Cloud Speech-to-Text & Text-to-Speech**:
  - Enable Cloud Speech-to-Text and Cloud Text-to-Speech APIs in Google Cloud Console.
  - Set `GOOGLE_SPEECH_API_KEY` in `.env`.

---

## Part 2: Local Sandbox Run Guide (Testing Without Credentials)

In local development and CI, all external telephony, Meta, and Speech AI services are fully mocked. You can exercise the full flow end-to-end using curl or Python.

### 1. Configuration for Mock Sandbox
In your `.env` file (or by default):
```env
TELEPHONY_PROVIDER=mock
STT_PROVIDER=mock
TTS_PROVIDER=mock
WHATSAPP_PROVIDER=mock
WHATSAPP_VERIFY_TOKEN=growcircle_webhook_token_2026
IVR_CALLBACK_BASE_URL=http://localhost:8000
```

---

### 2. Testing the Full IVR Telephony Lifecycle

#### Step 1: Simulate a Missed Call
```bash
curl -X POST "http://localhost:8000/ivr/missed-call?phone=9848011223"
```
**Expected Response:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
<Hangup/>
</Response>
```
*Behind the scenes: User is registered, and an outbound callback to `9848011223` is scheduled.*

#### Step 2: Caller Answers Callback (First-Time Caller)
```bash
curl -X POST "http://localhost:8000/ivr/callback?phone=9848011223"
```
**Expected Response:**
Prompts language selection DTMF menu (1=Telugu, 2=Hindi, 3=Gujarati) pointing to `/ivr/language-selection`:
```xml
<Response>
<Gather action="/ivr/language-selection?phone=9848011223" method="POST" numDigits="1" timeout="5">
<Say>Welcome to GrowCircle. For Telugu, press 1. For Hindi, press 2. For Gujarati, press 3...</Say>
</Gather>
</Response>
```

#### Step 3: Caller Selects Language (Press 1 for Telugu)
```bash
curl -X POST "http://localhost:8000/ivr/language-selection?phone=9848011223&Digits=1"
```
**Expected Response:**
Saves Telugu preference and prompts for district (1=Guntur, 2=NTR, 3=Tirupati, 4=Kurnool) pointing to `/ivr/district-selection`.

#### Step 4: Caller Selects District (Press 1 for Guntur)
```bash
curl -X POST "http://localhost:8000/ivr/district-selection?phone=9848011223&Digits=1"
```
**Expected Response:**
Saves Guntur preference and routes to Crop Menu (Press 1 for Banana).

#### Step 5: Caller Selects Crop (Press 1 for Banana)
```bash
curl -X POST "http://localhost:8000/ivr/crop-menu?phone=9848011223&Digits=1"
```
**Expected Response:**
Queries Phase 1 PostGIS engine for 3 nearest mandis, speaks prices in Telugu under 1 minute, and offers post-answer menu:
```xml
<Response>
<Gather action="/ivr/action-selection?phone=9848011223&amp;crop=banana" method="POST" numDigits="1" timeout="5">
<Say>నేటి అరటిపండు ధరలు: 1. గుంటూరు మార్కెట్, దూరం 0.0 కిలోమీటర్లు, ధర కిలో 25 రూపాయలు. 2. తెనాలి మార్కెట్, దూరం 24.5 కిలోమీటర్లు, ధర కిలో 24 రూపాయల 50 పైసలు... పంట అమ్మడానికి 1 నొక్కండి, రవాణా కోసం 2 నొక్కండి, ధరలు మళ్ళీ వినడానికి 9 నొక్కండి.</Say>
</Gather>
</Response>
```

#### Step 6: Caller Selects Post-Answer Action
- **Press 1 to Sell Produce**:
  ```bash
  curl -X POST "http://localhost:8000/ivr/action-selection?phone=9848011223&crop=banana&Digits=1"
  ```
  *Response: "మీ పంట అమ్మకం అభ్యర్థన నమోదైంది..." + Hangup. A lead is logged in the `inquiries` table.*
- **Press 2 for Transport**:
  ```bash
  curl -X POST "http://localhost:8000/ivr/action-selection?phone=9848011223&crop=banana&Digits=2"
  ```
  *Response: "మీ రవాణా అభ్యర్థన నమోదైంది..." + Hangup. A transport lead is logged.*
- **Press 9 to Repeat**:
  ```bash
  curl -X POST "http://localhost:8000/ivr/action-selection?phone=9848011223&crop=banana&Digits=9"
  ```
  *Response: Replays the 3 nearest mandis' spoken prices.*

---

### 3. Testing the WhatsApp Cloud API Webhook

#### Step 1: Verify Webhook Handshake
```bash
curl -X GET "http://localhost:8000/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=growcircle_webhook_token_2026&hub.challenge=test_challenge_abc123"
```
**Expected Output:** `test_challenge_abc123` with HTTP 200.

#### Step 2: Inbound Voice Note Simulation
```bash
curl -X POST "http://localhost:8000/whatsapp/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "919848011223",
            "type": "audio",
            "audio": {"id": "mock_voice_note_01"}
          }]
        }
      }]
    }]
  }'
```
**Expected Output:**
`{"status": "EVENT_RECEIVED", "processed_count": "1"}`
*Behind the scenes: Audio is transcribed via STT, Banana prices for user district are retrieved, and BOTH a formatted WhatsApp text message AND an audio voice note are sent back to the user.*

#### Step 3: Inbound Location Sharing Simulation
```bash
curl -X POST "http://localhost:8000/whatsapp/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "919848011223",
            "type": "location",
            "location": {"latitude": 16.3067, "longitude": 80.4365}
          }]
        }
      }]
    }]
  }'
```
**Expected Output:**
Replies with the 3 nearest mandis ranked by PostGIS geodesic distance with modal price per kg.

---

### 4. Running the Complete Automated Test Suite

```bash
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run all 44 unit and integration tests across Phase 1 and Phase 2
pytest -v

# Run linters
ruff check .
black --check .
```
All 44 tests pass in ~1.05s without requiring external network access or live credentials.
