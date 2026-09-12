# Gate R0 — Product Reconciliation

**Baseline:** `f23d181f3715053b063cf18d7889ffd9bff9c8fc`

**Purpose:** reconcile TelDrive Lab's documented product claims with the implementation that actually exists. This gate freezes feature expansion until existing capabilities have earned their status through integration and end-to-end evidence.

## Product truth

TelDrive Lab is the safe engineering control plane around the existing TelDrive system.

The product principle remains:

> Observe → understand → plan → authorize → execute through a controlled boundary → verify → record evidence.

A model, planner, UI, scheduler, or adapter is never itself the authority to mutate production storage.

## New completion standard

A capability is **not COMPLETE merely because code, a test, an adapter, or a contract exists**.

The progression is:

```text
PRIMITIVE
    ↓
IMPLEMENTED
    ↓
INTEGRATED
    ↓
OPERATIONAL
    ↓
END-TO-END VERIFIED
    ↓
DOCUMENTED
    ↓
COMPLETE
```

### Status meanings

- **PRIMITIVE** — isolated function, adapter, provider, schema, or contract exists.
- **IMPLEMENTED** — isolated tests demonstrate the capability.
- **INTEGRATED** — capability is connected to the Lab control plane and its real dependencies.
- **OPERATIONAL** — an operator can use the supported workflow and receive the intended result.
- **VERIFIED** — an end-to-end test proves the intended result and important failure boundaries.
- **COMPLETE** — all applicable stages above are satisfied and documentation matches the evidence.

Optional external providers may remain unavailable on a host without making the core Lab incomplete, but an integration must not be called operational merely because an adapter exists.

## Reconciled phase status at R0

| Phase | R0 status | Truth |
|---|---|---|
| 0 | COMPLETE | Foundation and separation are established. |
| 1 | PARTIAL | Health/backup/regression coverage is incomplete. |
| 2 | PARTIAL | Catalog exists, but authoritative TelDrive corpus discovery/ingestion is incomplete. |
| 3 | FOUNDATION COMPLETE | Durable JobStore/lease/retry primitives exist, but the full executor model is not complete. |
| 4 | PARTIAL | Local transfer is proven; rclone is an adapter/dry-run boundary rather than a complete backend. |
| 5 | PARTIAL | Deterministic planner/executor exists, but normal durable workflow integration is incomplete. |
| 6 | PARTIAL | Archive engine is strong, but the documented DISCOVER→HASH→DUPLICATE→POLICY→DRY-RUN→AUTH→QUEUE→TRANSFER→VERIFY→INDEX→AUDIT workflow is not fully integrated. |
| 7 | COMPLETE (core) | Integrity evidence and duplicate grouping are implemented and host-gated without production mutation. |
| 8 | PARTIAL | Lifecycle primitives exist but CLI exposure and physical/logical terminal-state reconciliation are incomplete. |
| 9 | PARTIAL | Backup scheduling exists, but a complete backup executor path is missing. |
| 10 | PARTIAL | Monitoring exists, but the full operational notification/health model is incomplete. |
| 11 | PARTIAL | CLI exposes many Lab operations, but documentation and implementation surfaces do not fully match. |
| 12 | PRIMITIVES | Storage/cache intelligence is implemented as local primitives, not yet a proven end-to-end product workflow. |
| 13 | PRIMITIVES | Read-only interoperability exists, but boundary hardening and integration evidence remain. |
| 14 | INCOMPLETE | Jellyfin/OTT is not operational; current code provides media primitives/integration contracts, not a proven TelDrive→library→Jellyfin playback workflow. |
| 15 | PROVIDER PRIMITIVES | OCR/STT/embedding/visual helpers exist, but provider integration and semantic quality are not established as a product pipeline. |
| 16 | INCOMPLETE | Advanced content search is separate from `td search`; authoritative corpus ingestion and unified search are missing. |
| 17 | ADVISORY PRIMITIVES | AI assistance is advisory, but product integration and end-to-end value are not complete. |
| 18 | ADVISORY | Storage analytics/recommendation primitives exist; operational integration remains incomplete. |
| 19 | SNAPSHOT PRIMITIVES | Snapshot/restore primitives exist, but the complete durable operational workflow is not proven. |
| 20 | CONTRACTS | Cross-project contracts exist; production integrations are not yet operational workflows. |
| 21 | EXPERIMENTAL | Experimental primitives exist and must remain isolated until proven. |
| 22 | INCOMPLETE | Control Center is a UI/API shell with default empty payloads rather than a live control-plane surface. |

## Critical product gaps

### 1. Corpus discovery is the foundation

The Lab must automatically discover the existing TelDrive corpus through an authoritative, bounded, incremental metadata interface.

```text
Existing TelDrive corpus
        ↓
Authoritative corpus discovery / ingestion
        ↓
Derived catalog
        ├── td search
        ├── duplicates
        ├── integrity
        ├── organization
        ├── archive
        └── media library
```

The operator must **not** be required to manually add every existing TelDrive file before Search or media workflows can understand the corpus.

### 2. TD Search must become one product surface

The intended search surface is:

```text
td search
 ├── filename/path
 ├── metadata
 ├── media metadata
 ├── full text
 ├── OCR
 ├── transcripts
 └── optional semantic layer
```

The existing basic catalog path/name search and the separate advanced content search must eventually converge behind this surface.

### 3. Media/OTT must prove the user outcome

The target workflow is:

```text
movie uploaded to TelDrive
        ↓
automatic discovery
        ↓
media metadata
        ↓
Jellyfin library exposure
        ↓
Jellyfin
        ↓
actual playback
```

An integration class, HTTP adapter, or media scanner alone is not sufficient evidence of completion.

## R0 cleanup rules

1. Do not start new feature phases merely to avoid fixing existing integration gaps.
2. Do not call adapters, contracts, mocks, or shallow capability tests end-to-end features.
3. Keep production TelDrive storage and database outside Lab ownership.
4. Keep the ₹0 constraint: no paid runtime dependency, paid API, or mandatory remote AI.
5. Prefer one canonical implementation over duplicate `extended.py`/`advanced.py` or overlapping retry/error systems.
6. Make resource-sensitive operations streaming/bounded where practical.
7. Non-loopback read-only APIs require explicit security controls; localhost remains the safe default.
8. Lab runtime state/cache paths must be rejected if they resolve inside protected production roots.
9. Caller-issued authorization must remain separate from planning/execution.
10. Release claims must be evidence-driven.

## R1–R5 reconciliation sequence

### R1 — Corpus Discovery

Deliver an authoritative, bounded, incremental TelDrive metadata discovery/ingestion path into the existing derived catalog. Preserve provenance and make repeated scans idempotent.

### R2 — Unified TD Search

Make `td search` operate over the discovered corpus and progressively unify filename/path, metadata, full text, OCR/transcripts, and optional semantic indexes without making any one provider mandatory.

### R3 — Operational Media/OTT

Build the real TelDrive media discovery → media catalog → Jellyfin library exposure path. Verify actual library visibility and playback using Lab-owned/test media before any production mutation.

### R4 — Durable Execution Reconciliation

Unify JobStore, Worker, TransferManager, rclone, Archive, Organization, Backup, Lifecycle, Verification, and Audit so every consequential workflow uses the same durable execution boundary. Ensure progress and VERIFYING state are real, not merely modeled.

### R5 — Live Control Center

Wire the Control Center to live catalog, jobs, transfers, media, search, health, and audit data only after the underlying control-plane workflows are operational.

## Release rule

Until R0 and its dependent reconciliation gates are satisfied, the repository must not describe Phases 12–22 as complete and must not claim that the optional media/search/control-center ecosystem is operational.
