# Phase 5: Farm Diary, Season Economics & Consumer Features

GrowCircle Phase 5 delivers financial empowerment for smallholder farmers and transparent market intelligence for everyday consumers.

---

## 1. Farm Diary & Season Economics

### 1.1 Cultivation Plot & Season Management
- Models: `FarmSeason` and `FarmDiaryEntry` in `backend/app/models/farm_diary.py`.
- Migration: `backend/alembic/versions/0005_phase5_diary_and_consumer.py`.
- REST Endpoints:
  - `POST /diary/seasons?farmer_id={id}`: Initialize cultivation season with area in acres, crop, variety, soil type, planting date, and expected yield.
  - `GET /diary/seasons/{id}`: Fetch season details with all recorded ledger entries.
  - `GET /diary/seasons/{id}/metrics`: Compute live economics (total costs, category breakdown, total revenue, P&L per acre, break-even price).
  - `GET /diary/seasons/{id}/mandi-comparison`: Benchmark realized sale price against daily Agmarknet mandi modal average across identical season dates.
  - `GET /diary/seasons/{id}/export?format=csv|json`: Full ledger data export.

### 1.2 Voice Entry with Mandatory Read-Back Confirmation
- Endpoint: `POST /diary/voice-entry`
- Voice simulation and transcription parsers extract category, numerical amounts, and transaction type.
- **Enforced Safety Protocol**:
  - The voice note is transcribed into text.
  - A spoken read-back prompt is generated in the farmer's language (English, Telugu, Hindi, or Gujarati).
  - The entry is **staged in draft status** until the user reviews and confirms (`readback_confirmed = True`), preventing recording errors.

### 1.3 Season Summary vs Mandi Average Comparison
- Automatically aggregates official daily mandi modal prices for the season's district over the planting-to-harvest interval.
- Compares the farmer's realized average price from direct institutional contracts with the mandi baseline.
- Displays the **Direct Selling Dividend** and price premium percentage (e.g. `+₹4.30/kg (+17.8%) Premium`).

### 1.4 Data Portability
- Single-click CSV and JSON downloads allow farmers to inspect, print, or share their records with agricultural credit officers, banks, or local cooperatives.

---

## 2. Consumer Price Center

### 2.1 "Price Today" for Any Crop
- Publicly accessible without login at `/[locale]/prices`.
- Covers **Banana, Tomato, Onion, and Green Chilli** with multi-district Andhra Pradesh mandi rates (Guntur, Tenali, Vijayawada, Kurnool, Madanapalle, Tirupati).
- Seamless switching between unit modes: `₹ / kg` for household buyers and `₹ / quintal` for institutional kitchens.
- 30-day historical interactive price curves displaying market volatility and daily mandi arrivals.

### 2.2 "Is it expensive this month?" Seasonality Analyzer
- Endpoint: `GET /consumer/seasonality/{crop_id}?district={district}`
- Compares current modal rates against the 30-day baseline benchmark:
  - **`expensive`**: Price $> +10\%$ above baseline. Provides advice on arrival bottlenecks and anticipated stabilization windows.
  - **`cheap`**: Price $< -10\%$ below baseline. Flags optimal bulk-buying opportunities for hostels and households.
  - **`fair`**: Price within $\pm10\%$ of seasonal norms.

### 2.3 Free WhatsApp & Telegram Price Drop Alerts
- Endpoint: `POST /consumer/alerts`
- Open, zero-login subscription: consumers specify phone number or Telegram handle, target commodity, district, and threshold price.
- Dispatches automated notifications when daily mandi prices drop below the chosen target.

---

## 3. Multilingual Coverage & Accessibility
- Complete translations across all 4 target languages:
  - English (`en`)
  - Telugu (`te`)
  - Hindi (`hi`)
  - Gujarati (`gu`)
- WCAG AA contrast ratio compliance verified across all UI color tokens and interactive elements.
- Touch-friendly targets ($\ge 44 \times 44$ px) and clear typography using modern system fonts.
