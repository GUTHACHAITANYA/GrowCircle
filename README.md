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

# Run tests (131/131 unit, integration, forecasting, anomaly, crop planning, and vision tests)
pytest -v

# Run ML Data Foundation & MLOps Pipeline (Phase ML-0)
python ml/data/backfill.py
python ml/data/cleaning.py
python ml/data/expectations.py
python ml/data/coverage.py
python ml/data/dataset_registry.py
python ml/tracking/mlflow_tracker.py

# Run ML Price Forecasting & Backtesting (Phase ML-1)
python ml/models/baselines.py
python ml/models/lightgbm_forecaster.py
python ml/evaluation/backtest.py

# Run ML Anomaly Detection Benchmark & Evaluation (Phase ML-2)
python ml/anomaly/generate_sample.py
python ml/anomaly/evaluate.py

# Run ML Crop Planning & Downside Risk Engine (Phase ML-3)
python ml/planning/backtest_planner.py

# Run ML Computer Vision Quality & Robustness Benchmark (Phase ML-4)
python ml/vision/evaluate_vision.py

# Run ML Voice & Chat Agent Benchmark Evaluation (Phase ML-6)
python -m ml.agent.eval_harness

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
# Visit:
# - http://localhost:3000/en/plan    (Crop Planning Guidance, Downside Ranges & Voice Advisor)
# - http://localhost:3000/en/prices  (Mandi Prices & Trends)
# - http://localhost:3000/en/portal  (Buyer Portal & 50km Radar Map)
# - http://localhost:3000/en/driver  (Transporter Portal & Freight Pooling)
# - http://localhost:3000/en/admin   (Admin Verification & Delivery Disputes)
# - http://localhost:3000/en/diary   (Farm Diary, Economics & Voice Ledger)
# - http://localhost:3000/en/privacy (DPDP Act 2023 Compliant Privacy Policy)
# - http://localhost:3000/en/terms   (Terms of Use & Fair Dealing Guidelines)
```

### 4. Core Endpoints & Doors
- **Phase 1 REST API**:
  - `GET /health`: DB, Redis connectivity, last fetch timestamp, stale data alert (>24h).
  - `GET /prices?crop=banana&state=andhra-pradesh&district=guntur`: Today's mandi prices.
  - `GET /nearby-mandis?lat=16.3067&lng=80.4365&crop=banana&limit=3`: PostGIS geodesic distance ranking.
  - `GET /history?mandi_id=ap-guntur-01&crop=banana&days=30`: 30-day modal price trend.
- **Phase 2 Phone (IVR) Door**:
  - `POST /ivr/missed-call`: Trigger callback call on missed call.
  - `POST /ivr/callback`: Language DTMF menu (1=te, 2=hi, 3=gu) and district prompt.
  - `POST /ivr/crop-menu`: Speaks 3 nearest mandis' prices under 1 minute.
  - `POST /ivr/action-selection`: Actions (1=sell lead, 2=transport lead, 9=repeat).
- **Phase 2 WhatsApp Door**:
  - `GET /whatsapp/webhook`: Meta Webhook challenge verification.
  - `POST /whatsapp/webhook`: Handles voice notes (transcribe > text + voice note reply), location pins, text queries, and driver commands (`AVAILABLE`, `PICKUP`, `DELIVER`, `TRIPS`).
- **Phase 3 Direct Selling & Matching Endpoints**:
  - `POST /market/auth/send-otp` & `POST /market/auth/verify-otp`: Phone-OTP authentication with JWT roles.
  - `POST /market/buyers/register`: Commercial buyer registration with Fernet AES-256 encrypted GST/Shop proof.
  - `GET /market/admin/buyers/pending` & `POST /market/admin/buyers/{id}/verify`: Admin approval workflow with on-demand in-memory proof decryption.
  - `POST /market/listings`: Farmer produce listing creation enforcing fresh in-app camera captures (<24h) and 3-photo checklist (`whole_lot`, `close_up`, `opened_crate`).
  - `POST /market/needs`: Recurring institutional demand posting.
  - `GET /market/matching/buyers-for-listing/{id}`: 50 km proximity matching scored by distance, quantity, grade, and reliability.
  - `GET /market/matching/group-supply`: Multi-farmer supply aggregator calculating total pooled volume and weighted average price.
  - `POST /market/offers` & `POST /market/offers/{id}/counter`: Negotiation timeline.
  - `POST /market/offers/{id}/accept`: Finalizes deal with read-back verification and generates secret 6-digit Delivery OTP.
  - `POST /market/telephony/masked-call`: Virtual bridge connecting buyer and farmer without exposing real phone numbers.
- **Phase 4 Transport & Logistics Endpoints**:
  - `POST /transport/transporters` & `GET /transport/transporters/{id}`: Transporter registration, vehicle capacity, and strict document compliance (DL, RC, insurance, fitness).
  - `PATCH /transport/transporters/{id}/availability`: Available-today toggle switch.
  - `GET /transport/matches/suggest`: Suggests top 3 verified drivers near pickup matched to load weight (<500kg auto, 500-1500kg mini truck, >1500kg truck) with indicative guide rates.
  - `GET /transport/pooling/plan`: Rule-based pooling engine grouping nearby farm pickups within 15 km going to the same institution.
  - `POST /transport/trips`: Creates trip assignment with Pickup OTP (4-digit) and Delivery OTP (6-digit).
  - `POST /transport/trips/{id}/verify-pickup`: Farm gate pickup handshake.
  - `POST /transport/trips/{id}/verify-delivery`: Buyer gate delivery handshake.
  - `POST /transport/trips/{id}/dispute` & `POST /transport/trips/{id}/resolve-dispute`: Delivery complaint with mandatory damage photo proof and Admin arbitration.
  - `POST /transport/trips/{id}/ratings`: Two-way mutual ratings updating reliability scores.
- **Phase 5 Farm Diary & Consumer Features Endpoints**:
  - `POST /diary/seasons` & `GET /diary/seasons/{id}`: Plot and cultivation season lifecycle tracking (area, crop, dates, expected yield).
  - `POST /diary/seasons/{id}/entries`: Ledger entries for costs, harvest yields, and direct sale revenue.
  - `POST /diary/voice-entry`: Natural language voice parsing with mandatory localized read-back confirmation prompt before saving.
  - `GET /diary/seasons/{id}/metrics`: Dynamic calculations of total cultivation cost, sales revenue, net profit/loss, profit/loss per acre, and break-even price per kg.
  - `GET /diary/seasons/{id}/mandi-comparison`: Automated benchmark against Agmarknet daily modal averages for the district over identical season dates, calculating farmer price premium and Direct Selling Dividend.
  - `GET /diary/seasons/{id}/export?format=csv|json`: Farmer records data portability on request.
  - `GET /consumer/seasonality/{crop_id}`: "Is it expensive this month?" seasonal analyzer evaluating current rates against baseline ($\pm10\%$) with plain-language buying advice.
  - `POST /consumer/alerts`: Zero-login price drop alert subscriptions via WhatsApp and Telegram.
- **Phase 6 Production, Security, DPDP & Telemetry Endpoints**:
  - `GET /metrics`: Standard Prometheus metrics exposition (throughput, latency histograms, telephony calls, deals, data freshness).
  - `GET /analytics/dashboard`: Privacy-friendly aggregated telemetry across all doors (WAU per door, total deals, trips, calls).
  - `POST /dpdp/consent`: Statutory consent registration (`consent_version`, `consent_purpose`).
  - `GET /dpdp/export`: DPDP Right to Data Portability (full user data dump in machine-readable JSON).
  - `POST /dpdp/delete-account`: DPDP Right to Erasure / Deletion (cryptographic PII anonymization and soft deletion).
  - `GET /dpdp/grievance`: Statutory Data Protection & Grievance Redressal Officer contact and 72-hour acknowledgment SLA.
  - `POST /feedback`: Multi-channel user feedback (web rating, WhatsApp voice notes, IVR 1-key input).
- **Phase ML-1 Price Forecasting Endpoint**:
  - `GET /forecast?mandi_id=ap-guntur-01&crop=banana&horizon=7`: Direct multi-horizon quantile price forecast (1, 3, 7, 14 days ahead) delivering median ($\hat{y}_{50}$) and calibrated 10th-90th percentile interval ($\hat{y}_{10}-\hat{y}_{90}$), data sufficiency level (`mandi_ml`, `proxy_hub_ml`, `seasonal_naive_baseline`), model version, plain note `"guidance only"`, and 4-language direction text (English, Telugu, Hindi, Gujarati).
- **Phase ML-2 Anomaly Review & Outage Endpoints**:
  - `GET /admin/anomalies/queue?status_filter=pending_review`: Admin review queue listing quarantined price, offer, and deal anomalies with reason codes, severities, and metrics payloads.
  - `POST /admin/anomalies/{id}/review`: Admin review action (`approve` or `reject`), releasing approved records to public endpoints with complete audit logs.
  - `GET /admin/anomalies/stats`: Aggregated review queue health metrics (pending, approved, rejected, auto-cleared by severity).
  - `GET /health/reporting-status`: Source outage monitoring tracking active vs expected reporting mandis by day-of-week.
- **Phase ML-3 Crop Planning & Crash Risk Guidance Endpoints**:
  - `GET /crop-plan?district=Guntur&month=7&farmer_id=1`: Ranks 3 to 5 candidate crops by expected profit per acre with downside risk scenarios, price-crash risk score (0-100), Cobweb crowding index, KVK-verified variety recommendations, personal farmer diary 50/50 blending, statutory KVK disclaimer, and concise 4-language voice advisory (< 45s audio).
- **Phase ML-4 Computer Vision Quality & Fraud Check Endpoints**:
  - `POST /vision/inspect`: Multi-task quality triage suggesting Banana/Tomato commercial grade (Grade A/B/C) with calibrated confidence, ripeness stage, defect hints, and photo fraud report. Enforces suggestive-only policy (never auto-rejects a farmer; low confidence mandates "buyer to check") and a 3.5s timeout with graceful fallback.
  - `POST /vision/fraud-check`: Photo integrity screening evaluating EXIF timestamp freshness (< 24h), GPS distance vs farm (< 25 km), perceptual near-duplicate hashes (dHash, pHash), and 2D FFT Moire screen patterns.
  - `POST /vision/collect`: Statutory DPDP-consented farmer photo intake queue preparing Label Studio annotation tasks across the 3-Photo Checklist.
- **Phase ML-5 Smarter Matching & Logistics Endpoints**:
  - `POST /logistics/rank-listings`: Listwise buyer-farmer ranking (LightGBM LambdaRank vs Rule baseline) with A/B testing gating, smallholder Four-Fifths exposure audit ($\ge 0.80$), and structured audit logging.
  - `POST /logistics/rate-guide`: Calibrated fair transport rate regression predicting ranges $[R_{\min}, R_{\text{est}}, R_{\max}]$ across vehicle classes, diesel fuel prices, road surface roughness (1.0 to 1.45), and night surcharges (1.15), with advisory disclaimer.
  - `POST /logistics/pool-routes`: Google OR-Tools multi-stop CVRPTW pooling with vehicle capacities, pickup time windows, road tortuosity (1.28x), and crop shelf-life limits (Tomato 18h, Banana 36h) reporting cost-per-kg savings vs separate trips.
  - `POST /logistics/rank-drivers`: Anti-monopoly driver matching with fatigue/equity leveling penalty $\exp(-N_{\text{recent}}/\tau)$ and Gini coefficient inequality monitoring.
  - `GET /logistics/data-sufficiency`: Honest statistical data scale documentation (minimum 1,200 sessions threshold before activating ML over rules).
  - `GET /logistics/audit-logs`: Immutable decision audit trail for algorithmic safety reviews.
- **Phase ML-6 Voice & Chat Agent Endpoints Speaking as "GrowCircle"**:
  - `POST /agent/chat`: Conversational natural speech/text turn with function calling across 9 strict tools, zero hallucinations (0.0%), and RAG agronomy answers with ICAR/ANGRAU citations.
  - `POST /agent/voice`: Phone/WhatsApp voice turn returning grounded text, intent, and audio synthesis link with sub-millisecond core processing latency.
  - `POST /agent/confirm-action`: Two-phase confirmation gate executing pending consequential actions (listing, accepting offers, booking transport) via DTMF 1 or spoken affirmative.
  - `GET /agent/eval-report`: Benchmark evaluation report across 725+ realistic utterances (WER, intent accuracy, tool accuracy, latency, and hallucination rates).
  - `POST /agent/consent-recording`: Statutory DPDP Act 2023 consent registration for audio collection to improve vernacular crop and mandi vocabularies.
- **Phase ML-7 Post-Launch Monitoring, Safe Releases & Trust Endpoints**:
  - `GET /monitoring/dashboard`: Consolidated post-launch trust dashboard reporting model health, drift, forecast error tracking, interval calibration, vision confidence, voice agent language failure rates, active alerts, and budget spend.
  - `GET /monitoring/drift`: Feature-level data drift (KS tests & PSI) and prediction drift reports.
  - `GET /monitoring/forecast-errors`: Daily forecast error tracking as actuals arrive with quantile calibration status.
  - `GET /monitoring/alerts` & `POST /monitoring/alerts/acknowledge`: Multi-tiered alerting engine for forecast error breaches, data ingestion outages, policy shocks, festival surges, and budget caps.
  - `POST /monitoring/feedback/report-wrong`: 1-key (IVR keypress 9/0), WhatsApp button, or Web flag error reporting.
  - `GET /monitoring/feedback/queue` & `POST /monitoring/feedback/{id}/review`: Human review queue promoting confirmed failure cases into golden CI evaluation datasets.
  - `POST /monitoring/release/deploy`, `POST /monitoring/release/rollback`, `POST /monitoring/release/promote`, `GET /monitoring/release/status`: Safe release lifecycle (Shadow mode, Canary deployment, and Automated Rollback to baseline upon metric degradation).
  - `GET /monitoring/cost` & `POST /monitoring/cost/record-call`: Telephony (STT, TTS), LLM, and SMS unit cost tracking, budget limits, and aggressive caching telemetry.

---

## Phase Documentation & Architecture Decisions
- [docs/phase1_price_engine.md](docs/phase1_price_engine.md)
- [docs/phase2_ivr_whatsapp_setup.md](docs/phase2_ivr_whatsapp_setup.md)
- [docs/phase3_direct_selling.md](docs/phase3_direct_selling.md)
- [docs/phase4_transport.md](docs/phase4_transport.md)
- [docs/phase5_diary_consumer.md](docs/phase5_diary_consumer.md)
- [docs/phase6_production_readiness.md](docs/phase6_production_readiness.md)
- [docs/decisions/0005-direct-selling-matching-architecture.md](docs/decisions/0005-direct-selling-matching-architecture.md)
- [docs/decisions/0006-transport-matching-pooling-architecture.md](docs/decisions/0006-transport-matching-pooling-architecture.md)
- [docs/decisions/0007-farm-diary-and-consumer-features.md](docs/decisions/0007-farm-diary-and-consumer-features.md)
- [docs/decisions/0008-production-readiness-and-launch.md](docs/decisions/0008-production-readiness-and-launch.md)
- [docs/decisions/0009-ml-data-foundation-and-mlops.md](docs/decisions/0009-ml-data-foundation-and-mlops.md)
- [docs/decisions/0010-price-forecasting-and-quantile-intervals.md](docs/decisions/0010-price-forecasting-and-quantile-intervals.md)
- [docs/decisions/0011-anomaly-detection-prices-deals-outages.md](docs/decisions/0011-anomaly-detection-prices-deals-outages.md)
- [docs/decisions/0012-crop-planning-and-crash-risk.md](docs/decisions/0012-crop-planning-and-crash-risk.md)
- [docs/decisions/0013-computer-vision-quality-and-fraud-detection.md](docs/decisions/0013-computer-vision-quality-and-fraud-detection.md)
- [docs/decisions/0014-smarter-matching-and-logistics.md](docs/decisions/0014-smarter-matching-and-logistics.md)
- [docs/decisions/0015-voice-and-chat-agent-architecture.md](docs/decisions/0015-voice-and-chat-agent-architecture.md)
- [docs/decisions/0016-post-launch-ml-monitoring-and-trust.md](docs/decisions/0016-post-launch-ml-monitoring-and-trust.md)
- [docs/ml/data_report.md](docs/ml/data_report.md)
- [docs/ml/vision_data_plan.md](docs/ml/vision_data_plan.md)
- [docs/ml/agent_eval_report.md](docs/ml/agent_eval_report.md)
- [docs/ml/review_checklist.md](docs/ml/review_checklist.md)
- [docs/ml/model_cards/price_forecast.md](docs/ml/model_cards/price_forecast.md)
- [docs/ml/model_cards/anomaly_detection.md](docs/ml/model_cards/anomaly_detection.md)
- [docs/ml/model_cards/crop_planning.md](docs/ml/model_cards/crop_planning.md)
- [docs/ml/model_cards/produce_vision_quality.md](docs/ml/model_cards/produce_vision_quality.md)
- [docs/ml/model_cards/matching_and_logistics.md](docs/ml/model_cards/matching_and_logistics.md)
- [docs/ml/model_cards/voice_chat_agent.md](docs/ml/model_cards/voice_chat_agent.md)
- [docs/ml/crop_planning_backtest_report.md](docs/ml/crop_planning_backtest_report.md)
- [docs/ml/data_gaps_farmer_input.md](docs/ml/data_gaps_farmer_input.md)
- [notebooks/ml5_logistics_pooling_savings.ipynb](notebooks/ml5_logistics_pooling_savings.ipynb)
- [docs/architecture/kafka_kubernetes_evaluation.md](docs/architecture/kafka_kubernetes_evaluation.md)
- [docs/legal/dpdp_act_compliance_checklist.md](docs/legal/dpdp_act_compliance_checklist.md)
- [docs/legal/privacy_policy.md](docs/legal/privacy_policy.md)
- [docs/legal/terms_of_use.md](docs/legal/terms_of_use.md)
- [docs/pilot/farmer_guide.md](docs/pilot/farmer_guide.md)
- [docs/pilot/village_helper_guide.md](docs/pilot/village_helper_guide.md)
- [docs/pilot/demo_call_script.md](docs/pilot/demo_call_script.md)
- [assets/brand/store_listing/store_listing_metadata.md](assets/brand/store_listing/store_listing_metadata.md)
