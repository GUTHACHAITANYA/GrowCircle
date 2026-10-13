# GrowCircle System Architecture

GrowCircle is built upon a **modular monolith** paradigm designed around the philosophy: **"One engine, five doors"**.

---

## 1. The One Engine, Five Doors Concept

Every user-facing channel ("door") communicates with the exact same unified FastAPI application ("engine"). Business rules, mandi price normalization, data validation, DPDP consent checks, and RBAC logic are enforced in a single place.

```mermaid
flowchart TD
    subgraph Doors ["Five Doors (Access Channels)"]
        IVR["Phone Call (IVR)<br/>Voice Prompts"]
        BOT["Bot Gateway<br/>WhatsApp / Telegram"]
        WEB["Web & PWA<br/>Next.js + i18n"]
        APP["Mobile App<br/>(Future Client)"]
        ADMIN["Admin Dashboard<br/>Verification & Audit"]
    end

    subgraph CoreEngine ["One Engine (FastAPI Modular Monolith)"]
        API_GW["FastAPI API Router & Auth / RBAC"]
        MANDI_SVC["Mandi Price Service<br/>& Quality Engine"]
        MATCH_SVC["Marketplace & Deal Matching"]
        LOGISTICS_SVC["Logistics & Driver Dispatch"]
        ML_SVC["Price Forecast & Guidance Engine"]
        PRIVACY_SVC["DPDP Consent & Call Masking"]
    end

    subgraph DataPlane ["Persistence & Async Tasks"]
        PG[("PostgreSQL + PostGIS<br/>Geospatial Data")]
        REDIS[("Redis Cache<br/>& Message Broker")]
        CELERY["Celery Workers<br/>Scheduled Agmarknet ETL"]
        DATA_GOV["data.gov.in<br/>(Agmarknet Mandi API)"]
    end

    IVR -->|REST / Webhooks| API_GW
    BOT -->|Webhook Events| API_GW
    WEB -->|REST / JSON| API_GW
    APP -->|REST / JSON| API_GW
    ADMIN -->|REST / JSON| API_GW

    API_GW --> MANDI_SVC
    API_GW --> MATCH_SVC
    API_GW --> LOGISTICS_SVC
    API_GW --> ML_SVC
    API_GW --> PRIVACY_SVC

    MANDI_SVC --> PG
    MATCH_SVC --> PG
    LOGISTICS_SVC --> PG
    ML_SVC --> PG
    PRIVACY_SVC --> PG

    MANDI_SVC --> REDIS
    API_GW --> REDIS

    CELERY -->|Periodic Fetch| DATA_GOV
    CELERY -->|Validate & Ingest| PG
    CELERY -->|Invalidate/Warm| REDIS
```

---

## 2. End-to-End Data Flow: Mandi Price Ingestion & Consumption

```mermaid
sequenceDiagram
    autonumber
    participant DGI as data.gov.in (Agmarknet)
    participant Worker as Celery Periodic Ingestion Worker
    participant Validator as Data Quality Guard
    participant DB as PostgreSQL (Mandi Records)
    participant Cache as Redis (Nearest Mandis Cache)
    participant Client as User Door (Web, Bot, or IVR)

    Worker->>DGI: Poll daily commodity prices with API Key
    DGI-->>Worker: Raw JSON response (Prices per quintal)
    Worker->>Validator: Inspect records (check 10x jumps, negative, min > max)
    alt Quality checks pass
        Validator->>DB: Upsert records with conversion (quintal -> kg/ton)
        Validator->>Cache: Refresh cache & invalidate outdated queries
    else Anomaly detected
        Validator-->>Worker: Flag anomaly, log warning, discard or hold for audit
    end

    Client->>Cache: Request nearest mandi prices (user coordinates/district, crop)
    alt Cache hit (< 24 hrs fresh)
        Cache-->>Client: Return prices with date, last_updated & freshness badge
    else Cache miss
        DB-->>Client: Compute nearest mandis via PostGIS distance & return
    end
```

---

## 3. Why a Modular Monolith?

### Decision Context
In early and high-growth stages of product development, microservices introduce excessive overhead: distributed tracing, eventual consistency challenges, duplicated schemas, network latency between internal services, and complex deployments.

### Guiding Principles:
1. **Single Source of Truth**: All five doors need identical validation for phone masking, crop units, and permissions. A shared codebase ensures zero divergence between the IVR prompt and the Web app.
2. **PostgreSQL + PostGIS**: Enables high-performance geospatial queries (calculating the 3 nearest mandis or drivers to a latitude/longitude point) with transaction safety.
3. **Internal Domain Boundaries**: Although deployed as a single application, code is organized into isolated domain packages (`mandi`, `marketplace`, `logistics`, `privacy`, `forecast`) with strict boundaries. If scaling demands separating a service (e.g. ML inference), the boundary is already clean.
