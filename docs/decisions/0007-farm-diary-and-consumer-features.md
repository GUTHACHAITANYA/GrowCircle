# ADR 0007: Farm Diary with Voice Read-Back Confirmation, Season Economics, and Consumer Price Intelligence

## Context
Across agricultural communities in India, smallholder farmers face severe information asymmetry at the farm gate. While wholesale buyers and commission agents understand daily market movements and margin structures, farmers rarely have real-time visibility into their own unit cost of production. Consequently:
1. **Unrecorded Cultivation Costs**: Small, distributed expenses on seed saplings, pesticide sprays, labour days, diesel for pump sets, and crate rentals go unrecorded, leaving farmers unable to calculate their true cost per kilogram.
2. **Arbitrary Farm-Gate Pricing**: Without knowing their break-even price (`Total Costs / Harvest Yield`), farmers often accept distress prices below cost of production.
3. **Unproven Direct-Selling Premium**: Farmers who sell directly to local institutions (hostels, schools, hotels) need verifiable proof of how much extra profit they retained compared to what the nearby wholesale mandi paid over the identical timeframe.
4. **Friction of Mobile Data Entry**: Rural farmers operating with wet or dusty hands in the field cannot navigate complex multi-field accounting forms. Voice notes provide accessibility, but speech-to-text without verification risks catastrophic accounting errors.
5. **Consumer Price Transparency**: Everyday consumers, families, and student hostel mess contractors need open, friction-free access to daily market rates ("Price Today"), 30-day price trends, seasonality insights ("is it expensive this month?"), and price-drop alerts over WhatsApp and Telegram without login barriers.

GrowCircle Phase 5 resolves these challenges by introducing the **Farm Diary & Season Economics Engine** alongside the **Consumer Price Center**.

---

## Decisions

### 1. Farm Diary Data Models & Ledger Architecture
- **`FarmSeason`**: Encapsulates a cultivation plot cycle:
  - `season_name`, `crop_id`, `variety`, `area_acres` (float), `soil_type`, `planting_date`, `harvest_date`, `expected_yield_kg`, `district`.
- **`FarmDiaryEntry`**: Granular immutable ledger entries classified into:
  - `cost`: Expenses across categories (`seeds`, `fertilizer`, `labour`, `irrigation`, `machinery`, `transport`, `other`).
  - `yield_log`: Harvest cuts recorded in kilograms (`quantity_kg`).
  - `sale_revenue`: Direct sales to institutions with quantity, unit price (₹/kg), and total revenue.
  - `voice_transcription` and `readback_confirmed` (boolean): Audit trail of transcription and explicit user confirmation.

### 2. Voice-First Entry with Mandatory Read-Back Confirmation
- Speech-to-text parsers automatically extract numerical amounts, dates, and category intent from spoken phrases in English, Telugu, Hindi, or Gujarati.
- **Mandatory Read-Back Confirmation Protocol**:
  - Voice entries are **never saved directly to the database**.
  - The engine parses the voice note and synthesizes a localized read-back prompt:
    - *Telugu*: `"ధృవీకరణ: 2026-10-12న కూలీ కోసం ₹5,000 ఖర్చు నమోదు చేయమంటారా?"`
    - *Hindi*: `"पुष्टि करें: 2026-10-12 को मजदूरी पर ₹5,000 का खर्च दर्ज करें?"`
    - *Gujarati*: `"ખાતરી કરો: 2026-10-12 ના રોજ મજૂરી પાછળ ₹5,000 નો ખર્ચ નોંધવો છે?"`
    - *English*: `"Confirming cost entry: ₹5,000 spent on labour on 2026-10-12. Save this entry?"`
  - The farmer must review or hear the spoken read-back prompt and tap/confirm "Confirm & Save Entry" (`readback_confirmed = True`) before the entry commits to the ledger.

### 3. Dynamic Economic Metrics & Mandi Comparison Engine
- Every ledger update recalculates:
  - **Total Cultivation Cost**: Sum of all `cost` entries.
  - **Total Realized Sales Revenue**: Sum of all `sale_revenue` entries.
  - **Profit / Loss Per Acre**:
    $$\text{P\&L per Acre} = \frac{\text{Total Revenue} - \text{Total Costs}}{\text{Area in Acres}}$$
  - **Break-Even Price**:
    $$\text{Break-Even Price per kg} = \frac{\text{Total Costs}}{\max(\text{Total Harvested kg}, \text{Expected Yield kg})}$$
- **Mandi Benchmark Comparison**:
  - The engine queries the Agmarknet `Price` table for the season's crop and district across the exact date range from `planting_date` to `harvest_date`.
  - Calculates the wholesale mandi modal average ($\bar{P}_{\text{mandi}}$).
  - Computes the farmer's realized direct-sale average price ($\bar{P}_{\text{actual}}$).
  - Calculates the **Direct Selling Dividend**:
    $$\Delta P = \bar{P}_{\text{actual}} - \bar{P}_{\text{mandi}}, \quad \text{Premium \%} = \frac{\Delta P}{\bar{P}_{\text{mandi}}} \times 100$$
  - Summarizes the exact extra cash retained by avoiding intermediate commissions (e.g. `+₹4.30/kg (+17.8%) Premium`).

### 4. Data Portability (Export on Request)
- Farmers can export their complete farm ledger at any time in **CSV** or **JSON** format without vendor lock-in (`GET /diary/seasons/{id}/export?format=csv`).

### 5. Consumer Features: "Price Today", Seasonality & Zero-Login Alerts
- **"Price Today" for Any Crop**: Instant lookup across Banana, Tomato, Onion, and Green Chilli across nearest mandis with 30-day interactive price curves.
- **"Is it expensive this month?" Seasonality Analyzer**:
  - Compares the current modal price against the historical baseline (excluding current date) or regional benchmark:
    - $\Delta > +10\%$: `expensive` badge (*"Expensive this month"*, with advice on price peaks and recovery windows).
    - $\Delta < -10\%$: `cheap` badge (*"Great time to buy!"*, highlighting bulk-buying opportunities).
    - $-10\% \le \Delta \le +10\%$: `fair` badge (*"Normal / Fair Price"*).
- **Zero-Login WhatsApp and Telegram Alerts**:
  - Consumers subscribe with only their mobile number or Telegram handle, target commodity, district, and target price (`POST /consumer/alerts`).
  - No passwords, OAuth, or authentication required, eliminating barriers to public price transparency.

---

## Status
Accepted and implemented. Verified via automated backend pytest suite (70 tests passing), frontend typecheck/lint, WCAG AA contrast verification, and interactive browser end-to-end testing across English and Telugu.
