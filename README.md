# TelDrive Lab

TelDrive Lab is a zero-cost, safety-first engineering control plane around an existing TelDrive deployment.

## Product boundary

TelDrive remains the production storage authority. TelDrive Lab provides deterministic observation, catalog/search, planning, controlled execution, verification, audit, monitoring, and read-only control surfaces around it.

The Lab does **not** require or ship a cloud AI service, speech-to-text provider, or local LLM runtime. Whisper and Ollama are intentionally out of scope.

## Core principles

- TelDrive remains the source of truth.
- Existing Telegram data is protected.
- Existing rclone mounts and services remain protected.
- No migration or re-upload of existing data.
- Lab sidecars are disposable and rebuildable.
- Read-only consumers wherever possible.
- Consequential mutation goes through explicit policy/authorization and controlled execution.
- Verification and audit evidence follow execution.
- ₹0 / $0 infrastructure.
- Resource-conscious for the i5-1235U / 8 GB RAM host.

## Current product

- authoritative corpus discovery and local catalog
- unified filename/path/content search
- media catalog and Jellyfin integration
- durable jobs, transfers, recovery, verification, and audit
- storage/cache intelligence and planning
- read-only metadata/API interoperability
- OCR, document fingerprints, deterministic local embeddings, and content indexing
- deterministic storage analytics and advisory plans
- snapshots, manifests, verification, and restore planning
- explicit cross-project contracts
- CAS and report-only deduplication primitives
- loopback-only read-only Control Center

## Safety invariant

```text
Observe → understand → plan → authorize → controlled execution → verify → record evidence
```

AI is not an authority. In the current product contract, no AI runtime is required for normal operation.

## Protected production foundation

- TelDrive production deployment
- PostgreSQL / PGroonga
- Telegram-backed storage
- `~/TelegramRaw`
- `~/TelegramDrive`
- existing rclone services
- existing TelDrive source repository

## Documentation

The repository intentionally keeps only current architectural and operational documentation. Historical phase/reconciliation documents have been removed from the active documentation set.

- `ARCHITECTURE.md` — system architecture
- `DATA_MODEL.md` — derived data model
- `JOB_MODEL.md` — durable execution model
- `PRODUCTION_BOUNDARY.md` — protected production boundary
- `SAFETY_CONTRACT.md` — safety invariants
- `DECISIONS.md` — durable architecture decisions
- `ROADMAP.md` — current capability and release status
- `docs/OPERATIONS.md` — operational procedures
- `docs/RELEASE_CHECKLIST.md` — release gate
