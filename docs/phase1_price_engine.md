# Phase 1: Price Engine Documentation

## Overview
GrowCircle Phase 1 establishes the production price engine for **Andhra Pradesh** and **Banana**, architected as a modular row-based foundation ready to support all Indian states and crops.

Key capabilities delivered:
1. **Docker Compose Infrastructure**: PostgreSQL 16 + PostGIS 3.4, Redis 7, FastAPI backend, Celery worker & beat scheduler.
2. **PostGIS Spatial Engine**: Nearest mandis computed via geodesic spherical distance (`ST_Distance` on WGS84 geography) indexed via GIST.
3. **Agmarknet Daily Ingestion**: Celery beat automated daily fetcher with quintal-to-kg/ton conversions, idempotent upserts, and fallback seed data.
4. **Data Quality & Anomaly Guards**: Strict min <= modal <= max validation, positive price assertions, and 10x spike anomaly detection.
5. **Freshness & Stale Alerting**: Health checks reporting last fetch timestamp and flagging data older than 24 hours.
6. **Geocoding Pipeline**: Nominatim OpenStreetMap geocoding with caching and CSV manual correction overrides (`mandi_coordinates_override.csv`).
7. **FastAPI Endpoints**: 4 high-performance async endpoints for prices, nearby mandis, historical trends, and system health.
8. **Telegram Bot Door**: Responds to "banana price" or location sharing with the 3 nearest mandis in Telugu, English, Hindi, and Gujarati.
9. **Web Price Today Page**: Fast, accessible, multilingual price viewer (`/en/prices`, `/te/prices`, etc.) with responsive SVG 30-day modal price trend chart and unit toggle.

---

## Architecture & Data Flow

```
                      +-----------------------------+
                      |   data.gov.in / Agmarknet   |
                      +--------------+--------------+
                                     |
                                     v
+------------------+         +---------------+         +---------------------+
|   Celery Beat    | ------> | Celery Worker | ------> | DataQualityValidator|
| (Daily 06:00 IST)|         +-------+-------+         +----------+----------+
+------------------+                 |                            | Validated
                                     v                            v
                            +-----------------+        +---------------------+
                            | Redis 7 (Queue) |        | PostgreSQL+PostGIS  |
                            +-----------------+        |   - crops           |
                                                       |   - mandis (POINT)  |
                                                       |   - prices (upsert) |
                                                       |   - ingestion_logs  |
                                                       +----------+----------+
                                                                  |
                                       +--------------------------+--------------------------+
                                       |                                                     |
                                       v                                                     v
                            +--------------------+                                +--------------------+
                            |   FastAPI REST     |                                | Telegram Bot Door  |
                            | - /prices          |                                | - GPS Location     |
                            | - /nearby-mandis   |                                | - "banana price"   |
                            | - /history         |                                +--------------------+
                            | - /health          |
                            +----------+---------+
                                       |
                                       v
                            +--------------------+
                            |  Next.js Frontend  |
                            |  /[locale]/prices  |
                            +--------------------+
```

---

## Environment Variables

Copy `.env.example` to `.env`:

```bash
# Database & Spatial
POSTGRES_USER=growcircle
POSTGRES_PASSWORD=growcircle_secret
POSTGRES_DB=growcircle_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://growcircle:growcircle_secret@postgres:5432/growcircle_db
DATABASE_URL_SYNC=postgresql+psycopg://growcircle:growcircle_secret@postgres:5432/growcircle_db

# Redis & Celery
REDIS_URL=redis://redis:6379/0

# External APIs
DATA_GOV_IN_API_KEY=your_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# App Settings
ENVIRONMENT=production
DEBUG=false
```

---

## Running with Docker Compose

To start all services together:

```bash
# 1. Start containers
docker-compose up -d

# 2. Run database migrations
docker-compose exec backend alembic upgrade head

# 3. Seed initial AP mandis, crops, and prices
docker-compose exec backend python -m backend.scripts.seed_data

# 4. (Optional) Run geocoding script for new mandis
docker-compose exec backend python -m backend.scripts.geocode_mandis
```

---

## Local Development (Without Docker)

### Backend:
```bash
# 1. Activate Python virtualenv
.\.venv\Scripts\Activate.ps1

# 2. Run test suite
pytest -v

# 3. Run linters
ruff check .
black --check .

# 4. Start FastAPI server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Web Frontend:
```bash
cd web
npm run dev
# Open http://localhost:3000/en/prices or http://localhost:3000/te/prices
```

---

## API Endpoints & Sample Requests

### 1. System Health & Freshness Alert
Checks DB, Redis, and whether the latest mandi price is older than 24 hours.

```bash
curl -X GET "http://localhost:8000/health"
```
**Sample Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "last_fetch_at": "2026-10-13T06:00:00Z",
  "stale_data_flag": false,
  "stale_threshold_hours": 24
}
```

### 2. Today's Prices by State & District
Returns current prices with quintal, kg, and ton breakdowns.

```bash
curl -X GET "http://localhost:8000/prices?crop=banana&state=andhra-pradesh&district=guntur"
```
**Sample Response:**
```json
[
  {
    "crop_id": "banana",
    "crop_name": "Banana",
    "mandi_id": "ap-guntur-01",
    "mandi_name": "Guntur Fruit Market",
    "district": "Guntur",
    "state": "Andhra Pradesh",
    "date": "2026-10-13",
    "variety": "Robusta",
    "grade": "FAQ",
    "price_per_quintal": { "min": 2200.0, "max": 2800.0, "modal": 2500.0 },
    "price_per_kg": { "min": 22.0, "max": 28.0, "modal": 25.0 },
    "price_per_ton": { "min": 22000.0, "max": 28000.0, "modal": 25000.0 },
    "source": "agmarknet"
  }
]
```

### 3. Nearest 3 Mandis (PostGIS Spatial Geodesic Distance)
Returns mandis ranked by distance from user GPS coordinates.

```bash
curl -X GET "http://localhost:8000/nearby-mandis?lat=16.3067&lng=80.4365&crop=banana&limit=3"
```
**Sample Response:**
```json
[
  {
    "mandi_id": "ap-guntur-01",
    "name": "Guntur Fruit Market",
    "district": "Guntur",
    "distance_km": 0.0,
    "lat": 16.3067,
    "lng": 80.4365,
    "modal_price_per_kg": 25.0,
    "modal_price_per_quintal": 2500.0,
    "date": "2026-10-13"
  },
  {
    "mandi_id": "ap-tenali-01",
    "name": "Tenali Agricultural Market",
    "district": "Guntur",
    "distance_km": 24.8,
    "lat": 16.243,
    "lng": 80.64,
    "modal_price_per_kg": 24.5,
    "modal_price_per_quintal": 2450.0,
    "date": "2026-10-13"
  },
  {
    "mandi_id": "ap-vijayawada-01",
    "name": "Vijayawada Wholesale Mandi",
    "district": "NTR",
    "distance_km": 32.1,
    "lat": 16.5062,
    "lng": 80.648,
    "modal_price_per_kg": 26.0,
    "modal_price_per_quintal": 2600.0,
    "date": "2026-10-13"
  }
]
```

### 4. 30-Day Historical Trend
Returns chronological price records for charting.

```bash
curl -X GET "http://localhost:8000/history?mandi_id=ap-guntur-01&crop=banana&days=30"
```
**Sample Response:**
```json
{
  "mandi_id": "ap-guntur-01",
  "mandi_name": "Guntur Fruit Market",
  "crop_id": "banana",
  "crop_name": "Banana",
  "points": [
    { "date": "2026-09-14", "modal_price": 2400.0 },
    { "date": "2026-09-15", "modal_price": 2420.0 },
    { "date": "2026-10-13", "modal_price": 2500.0 }
  ]
}
```

---

## Telegram Bot Interface

The Telegram bot door allows users to query prices without installing the web app:
- Send `"banana price"` or `"అరటిపండు ధర"`: Returns today's state average and district modal prices.
- Share GPS Location: Calculates the 3 nearest mandis and formats response in the user's selected language (Telugu, English, Hindi, Gujarati).
- Brand header: Every response includes the translated brand name (e.g. `గ్రో సర్కిల్ | రైతు నుండి ప్రతిఒక్కరికీ, సంపూర్ణ వలయం`).

---

## Verification & Testing Summary

1. **Python Unit & Integration Tests**:
   - 22/22 tests passing in `backend/tests/`.
   - Unit conversions (quintal <-> kg <-> ton) validated.
   - PostGIS distance ordering validated against known geodesic coords.
   - Data quality validator rejects non-positive prices, invalid min > max, modal out of bounds, and flags 10x anomalies.
   - API endpoints (`/prices`, `/nearby-mandis`, `/history`, `/health`) tested with mock database.
2. **Web Frontend Verification**:
   - TypeScript `tsc --noEmit` passed with 0 errors.
   - ESLint passed with 0 warnings.
   - WCAG AA contrast ratio tests passed (all pairs >= 4.5:1).
   - Next.js production build (`next build`) successfully prerendered 16 static routes.
   - Visual verification via headless browser on `/en/prices` and `/te/prices` confirming unit switching, SVG modal trend chart, and Telugu typography.
