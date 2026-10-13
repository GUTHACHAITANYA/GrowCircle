# ADR 0003: Price Engine Architecture, Spatial Queries, and Ingestion Pipeline

## Context
GrowCircle requires accurate, near-real-time mandi prices across India. In Phase 1, we implement the price engine for **Andhra Pradesh** and **Banana**, designed such that expanding to all 28 states and hundreds of crops requires only adding rows, without code changes.

The engine must support:
1. Spatial search: finding the 3 nearest mandis to any user coordinates (GPS or district center).
2. Daily automated ingestion from Agmarknet / data.gov.in.
3. Unit normalization (Quintal, Kilogram, Metric Ton).
4. Data quality validation, anomaly detection, and freshness alerting.
5. Multichannel access: Web UI and Telegram bot door.

## Decisions

### 1. Database & Geospatial Architecture
- **PostgreSQL 16 + PostGIS 3.4**: Selected for native spatial indexing (`GIST`) and spherical distance calculations (`ST_Distance(geography)`).
- **Spatial Schema**:
  - `Mandi.location`: Stored as PostGIS `Geometry('POINT', 4326)`.
  - Spatial queries execute `ST_Distance(location::geography, ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography)` returning true geodesic distances in meters (converted to kilometers).
  - SpatialPoint SQLAlchemy TypeDecorator allows seamless in-memory SQLite testing in CI environments without requiring native SpatiaLite C binaries.

### 2. Normalization & Storage Units
- **Base Storage**: Raw mandi data from Agmarknet is reported in Indian **Quintals** (100 kg). Prices are stored in DB as `min_price_quintal`, `max_price_quintal`, and `modal_price_quintal` using `Numeric(10, 2)`.
- **Derived Units**: Computed dynamically or on ingestion:
  - `1 Quintal = 100 kg`: `price_per_kg = price_per_quintal / 100`
  - `1 Metric Ton = 10 Quintals = 1,000 kg`: `price_per_ton = price_per_quintal * 10`
- Both the FastAPI JSON schemas and Next.js frontend support user-driven unit toggles without loss of precision.

### 3. Idempotent Upsert & Ingestion
- Daily fetch runs via Celery Beat at 06:00 IST (00:30 UTC).
- Composite unique key on `prices`: `(mandi_id, crop_id, date, variety, grade)`.
- Ingestion uses PostgreSQL `ON CONFLICT (mandi_id, crop_id, date, variety, grade) DO UPDATE` to ensure rerunning jobs is safe and idempotent.

### 4. Data Quality & Anomaly Guards
- Prior to upsert, every raw record passes through `DataQualityValidator`:
  - Required fields present (`mandi_id`, `crop_id`, `date`, `modal_price`).
  - Strict price ordering: `0 < min_price <= modal_price <= max_price`.
  - Statistical anomaly detection: flags records where the price spikes by >10x or crashes to <0.1x compared to the previous known 7-day average.
- Every fetch run writes an audit record into `ingestion_logs`.

### 5. Freshness Alerting & Health Checks
- The `/health` endpoint checks:
  1. PostgreSQL database connectivity.
  2. Redis broker connectivity.
  3. Last successful price ingestion timestamp.
  4. `stale_data_flag`: `true` if newest price record is older than 24 hours.

## Consequences
- Clean separation between storage (quintals) and presentation (kg/ton/quintal).
- Adding new states (e.g., Maharashtra, Telangana) or crops (e.g., Tomato, Onion) only requires adding seed records in `crops` and `mandis`.
- Robust fallback mechanism allows local development and CI testing even during data.gov.in API downtime.
