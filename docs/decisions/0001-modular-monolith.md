# ADR 0001: Adopt Modular Monolith Architecture

## Status
Accepted

## Context
GrowCircle requires multiple user access channels: Web/PWA, IVR cloud telephony, WhatsApp bot, Admin portal, and future mobile clients. Each channel needs identical business rules for:
- Agmarknet daily price normalization and units (quintal to kg/ton).
- DPDP Act compliance (user consent, phone number masking, document reference encryption).
- Geographic queries (nearest 3 mandis and drivers).
- Role-based permissions.

Adopting microservices early introduces substantial operational latency, distributed transactions, data consistency hurdles, and increased DevOps complexity.

## Decision
We adopt a **modular monolith** built with **FastAPI**, **PostgreSQL + PostGIS**, and **Redis/Celery**:
1. All client channels interact with a single API layer ("one engine, five doors").
2. Code is cleanly decoupled into modular Python domains (`mandi`, `marketplace`, `logistics`, `ml`, `privacy`).
3. Shared database schema with PostGIS spatial indices.
4. Celery processes asynchronous Agmarknet ingestion without blocking user requests.

## Consequences
- **Positive**: Single source of truth, immediate data consistency, simpler deployment, zero cross-service RPC overhead.
- **Negative**: All domains share the same deployment artifact and scaling profile.
- **Mitigation**: Domain isolation ensures individual components can be extracted into standalone services if throughput requires it in the future.
