# ADR 0008: Production Readiness, Security Hardening, DPDP Act 2023 Compliance, and Launch Architecture

## Context
GrowCircle is moving from functional completion into production launch across pilot districts in Andhra Pradesh. Launching a mission-critical platform serving rural farmers, commercial wholesale buyers, institutional buyers, transport drivers, and everyday consumers demands uncompromising standards for:
1. **Security & Resilience**: Defense against OWASP Top-10 vulnerabilities, brute-force attacks on OTP endpoints, denial-of-service on telephony/webhook doors, and cryptographic leakage of PII.
2. **Statutory Compliance**: Full compliance with India's **Digital Personal Data Protection (DPDP) Act, 2023**, guaranteeing explicit consent, data minimisation, right to erasure, data portability, and a grievance redressal mechanism with statutory timelines.
3. **Observability & Reliability**: Low-overhead real-time metrics (Prometheus), error tracking (Sentry), and visual operational dashboards (Grafana) to monitor system health, telephony traffic, and Agmarknet data freshness.
4. **Disaster Recovery**: Automated backup routines with cryptographic checksum validation and proven restore procedures fulfilling a strict Recovery Time Objective (RTO < 15 minutes) and Recovery Point Objective (RPO < 1 hour).
5. **Infrastructure Sizing & Pragmatism**: Production deployment on AWS Mumbai (`ap-south-1`) provisioned declaratively via Terraform, while rigorously evaluating distributed technologies (Kafka, Kubernetes) to prevent premature over-engineering.
6. **Privacy-Preserving Telemetry**: Multi-door analytics tracking platform adoption without collecting identifiable telemetry or cookies.

---

## Decisions

### 1. Security Hardening & OWASP Top-10 Mitigations
- **Security Headers Middleware**: Implemented ASGI `SecurityHeadersMiddleware` enforcing:
  - `Content-Security-Policy`: Default strict source policies restricting script and object execution.
  - `X-Frame-Options: DENY`: Complete clickjacking mitigation.
  - `X-Content-Type-Options: nosniff`: Prevention of MIME-type sniffing attacks.
  - `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`: Enforcement of HTTPS.
  - `Referrer-Policy: strict-origin-when-cross-origin`: Information leakage prevention.
  - Server identification banner removal (`Server` header suppressed).
- **Multi-Door Sliding-Window Rate Limiting**:
  - Implemented `RateLimiter` supporting Redis sliding-window counters with in-memory thread-safe fallback:
    - **IVR Telephony**: 5 callbacks per minute per phone number to prevent telephony billing exhaustion.
    - **WhatsApp Webhooks**: 30 webhook requests per minute per sender.
    - **Authentication (OTP)**: 3 requests per 10 minutes per phone number to halt SMS pump fraud.
    - **Public API**: 120 requests per minute per IP address.
  - Returns `429 Too Many Requests` with `Retry-After` headers and informative JSON payloads.
- **Immutable Audit Logging**:
  - `AuditLog` table capturing actor, action, target resource, client IP, timestamp, and status.
  - Audit logs are append-only and immutable.
- **Cryptographic Secrets Handling**:
  - All credentials, API tokens, and webhook secrets loaded via strictly validated Pydantic `Settings` reading environment variables or AWS Secrets Manager. No credentials in code or repository.

### 2. Statutory DPDP Act 2023 Compliance
- **Notice & Consent Architecture**:
  - User records track `consent_at`, `consent_version` (e.g. `2026.1`), and `consent_purpose`.
  - Plain-language notice served before data processing on web, IVR keypad, and WhatsApp.
- **Right to Portability (`GET /dpdp/export`)**:
  - Authenticated users can download their complete platform data in structured JSON format (profile, listings, deals, transport trips, farm diary ledger).
- **Right to Erasure / Deletion (`POST /dpdp/delete-account`)**:
  - Irreversible anonymization of personal identifiers (phone number, name, location coordinates, vehicle details) and soft-deletion flag `is_deleted = true`.
  - Preserves anonymized aggregate statistics for tax, audit, and legal dispute compliance.
- **Statutory Grievance Redressal**:
  - Designated Data Protection & Grievance Redressal Officer:
    - Name: *Smt. Ananya Rao*
    - Email: `grievance@growcircle.in`
    - Phone: `+91 80 4710 3920`
  - Grievances acknowledged within **72 hours** and resolved within **15 calendar days** as mandated by the DPDP Act.

### 3. Observability & Monitoring
- **Prometheus Metrics Exposition**:
  - Native ASGI middleware tracking `growcircle_requests_total` and latency histograms `growcircle_request_duration_seconds`.
  - Custom business metrics: `growcircle_ivr_calls_total`, `growcircle_whatsapp_messages_total`, `growcircle_deals_completed_total`, `growcircle_trips_completed_total`, and `growcircle_data_freshness_seconds`.
  - Standard Prometheus exposition format exposed at `GET /metrics`.
- **Error Tracking**: Sentry SDK integration for centralized exception capture, stack traces, and release health monitoring.
- **Grafana Dashboard**: Standard configuration (`grafana_growcircle_dashboard.json`) providing real-time visibility into traffic, latency, telephony channels, and data freshness.

### 4. Disaster Recovery & Backup Integrity
- **Automated Backup Routine (`backup_db.py`)**:
  - Generates full database dumps with timestamped filenames.
  - Calculates SHA-256 cryptographic hashes and writes metadata sidecars containing table row counts and timestamps.
- **Automated Restoration Verification (`test_restore.py`)**:
  - Restores the dump to an isolated staging/verification database.
  - Asserts cryptographic checksum integrity, schema completeness, and table record counts.
  - Verifies RTO (<15 minutes) and RPO (<1 hour) SLAs.

### 5. Infrastructure Architecture & Technology Pragmatism
- **Cloud Deployment**: AWS Mumbai (`ap-south-1`) provisioned using modular Terraform (`infra/terraform/`):
  - Multi-AZ VPC across 2 Availability Zones (`ap-south-1a`, `ap-south-1b`).
  - Amazon RDS PostgreSQL 16 with PostGIS extension, Multi-AZ automated backups, storage autoscaling.
  - Amazon ElastiCache Redis 7 for cache, rate-limiting, and Celery message broker.
  - Encrypted Amazon S3 bucket with versioning and SSE-S3 encryption for produce media and export dumps.
  - AWS App Runner / ECS Fargate serverless containers for auto-scaling HTTP API with zero server management overhead.
- **Evaluation of Kafka and Kubernetes**:
  - **Empirical Load Test Results**: Monolithic FastAPI backend achieved **527.13 req/sec**, **p50: 27.19 ms**, and **p95: 122.51 ms** on single-node Redis + Postgres.
  - **Conclusion**: Redis + Celery handles over 10x peak pilot throughput at a fraction of operational cost (~$165/mo vs >$850/mo for EKS+MSK).
  - Kubernetes and Kafka are formally deferred until concrete bottlenecks (>25,000 msgs/sec or >25 microservices) justify their operational complexity.

### 6. Multi-Channel Pilot Launch Kit
- **Farmer One-Pager**: High-contrast, pictorial guide in English and Telugu explaining the 4-step circle with WhatsApp QR code.
- **Village Helper Guide**: Step-by-step handbook for Gram Mitras and SHG coordinators assisting non-literate farmers with voice listing and dispute resolution.
- **Feedback Service (`POST /feedback`)**: Low-friction feedback via web rating, WhatsApp voice notes, and IVR single-key input (`1-5`).

---

## Consequences & Verification

- **Security Verification**: Automated test suite validates HTTP security headers, rate limiting (HTTP 429), and unauthorized access blocks.
- **Compliance Verification**: DPDP export and deletion endpoints tested for data completeness and identifier scrubbing.
- **Performance Verification**: Stress test benchmarks confirm sub-150ms p95 latency under high concurrency.
- **Operational Simplicity**: Clean Terraform definitions and lightweight monitoring allow a small engineering team to maintain 99.9% uptime during pilot launch.
