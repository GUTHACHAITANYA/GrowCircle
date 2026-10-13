# GrowCircle (గ్రో సర్キల్ / ग्रो सर्कल / ગ્રો સર્કલ)
> *"Farm to everyone, full circle"*

GrowCircle is a voice-first platform that connects the whole fruit-and-vegetable ecosystem in India: farmers, buyers (hostels, colleges, schools, hotels, shops), transport drivers, and everyday consumers.

---

## The Four Core Flows
1. **Know the Price**: Real-time mandi prices (state > district > mandi) per crop from Agmarknet with distance-based nearest mandis, localized in the user's language (Telugu, Hindi, Gujarati, English).
2. **Find a Buyer / Find Supply**: Verified institutional buyers post demand; farmers list produce with photos/voice notes; offers and counter-offers with privacy-preserving masked calls.
3. **Move the Produce**: Verified local drivers (goods autos, mini-trucks); 3 nearest drivers suggested post-deal; pickup and delivery verification via OTP; two-way rating.
4. **Plan Ahead**: Farm diary, transparent price forecasts with strict ML baselines and uncertainty bounds, crop planning guidance, and consumer price alerts.

---

## One Engine, Five Doors
Every interface interacts with the exact same unified FastAPI backend:
- **Phone Call (IVR)**: Cloud telephony voice prompts in local languages for low-literacy users.
- **WhatsApp / Telegram Bot**: Conversational voice notes and quick buttons.
- **Web / PWA**: Mobile-first installable Progressive Web App with high-contrast UI and offline capabilities.
- **Mobile App**: Native/hybrid client (planned).
- **Admin Panel**: Operational dashboard for verification queues, dispute mediation, and data health monitoring.

---

## Repository Structure

```text
├── assets/
│   └── brand/           # Canonical logo vectors (mark & full), design tokens (tokens.json), and icons
├── backend/             # FastAPI backend (app, models, schemas, services, api, jobs, tests, alembic)
├── web/                 # Next.js PWA with brand design system and next-intl localization
├── ivr/                 # Telephony IVR flow definitions and audio prompt mappings
├── whatsapp/            # WhatsApp/Telegram webhook bots and message templates
├── ml/                  # ML pipelines, backtesting benchmarks, feature stores, and serving
├── infra/               # Docker, compose, CI/CD, and deployment infrastructure
└── docs/                # Architecture diagrams, brand guide, and Architecture Decision Records (ADRs)
```

---

## Non-Negotiable Engineering Principles
- **No Invented Data**: Every price comes directly from verified database records with timestamps. Prices older than 24 hours are clearly flagged.
- **Data Quality Safeguards**: Automatic detection and rejection of anomalous inputs (negative numbers, 10x spikes, minimum price exceeding maximum).
- **DPDP Act Privacy**: Strict consent records, masked contact numbers, encrypted document references, and zero data leakage.
- **No Financial Custody**: GrowCircle connects parties; we do not process or hold transactions.
- **Accessible & Multilingual First**: Minimum 44px touch targets, WCAG AA contrast ratio (4.5:1 text, 3:1 graphical elements), zero emojis in UI, and full i18n support without hardcoded text.
- **ML Honesty**: Every predictive model must strictly outperform naive baselines on out-of-time backtests and report uncertainty bounds. Predictions are labeled "guidance only".

---

## Local Development Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+ & npm
- Docker & Docker Compose (for PostgreSQL with PostGIS & Redis)

### 1. Docker Compose (Full Stack)
```bash
docker-compose up -d
docker-compose exec backend alembic upgrade head
docker-compose exec backend python -m backend.scripts.seed_data
```

### 2. Backend Local Development
```bash
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run tests (22/22 unit & integration tests)
pytest -v

# Run linters
ruff check .
black --check .

# Start FastAPI server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Web Frontend (Next.js)
```bash
cd web
npm install
npm run dev
# Visit http://localhost:3000/en/prices or http://localhost:3000/te/prices
```

### 4. Core Endpoints (Phase 1)
- `GET /health`: DB, Redis connectivity, last fetch timestamp, stale data alert (>24h).
- `GET /prices?crop=banana&state=andhra-pradesh&district=guntur`: Today's mandi prices with quintal, kg, and ton breakdowns.
- `GET /nearby-mandis?lat=16.3067&lng=80.4365&crop=banana&limit=3`: PostGIS geodesic distance ranking of nearest mandis.
- `GET /history?mandi_id=ap-guntur-01&crop=banana&days=30`: 30-day modal price chronological series.

For detailed architecture and curl examples, see [docs/phase1_price_engine.md](docs/phase1_price_engine.md).

