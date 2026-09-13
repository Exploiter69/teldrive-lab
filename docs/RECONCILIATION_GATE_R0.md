# Gate R0 — Product Reconciliation (Historical Baseline)

**Baseline:** `f23d181f3715053b063cf18d7889ffd9bff9c8fc`

**Record status:** Historical R0 baseline. This document records the evidence state and product gaps that existed when R0 began. It is retained as audit evidence and must not be read as the current status of the repository. Current status is maintained in `ROADMAP.md`, `docs/PHASES_12_22_IMPLEMENTATION_STATUS.md`, and the R1–R6 completion documents.

**Purpose:** reconcile TelDrive Lab's documented product claims with the implementation that actually existed at the R0 baseline. R0 froze feature expansion until existing capabilities had earned their status through integration and end-to-end evidence.

## Product truth

TelDrive Lab is the safe engineering control plane around the existing TelDrive system.

The product principle remains:

> Observe → understand → plan → authorize → execute through a controlled boundary → verify → record evidence.

A model, planner, UI, scheduler, or adapter is never itself the authority to mutate production storage.

## Completion standard

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

## Reconciled phase status at R0 — historical only

The following table is intentionally preserved as the R0 starting point. It is **not** the current project status.

| Phase | R0 status | Truth at the R0 baseline |
|---|---|---|
| 0 | COMPLETE | Foundation and separation were established. |
| 1 | PARTIAL | Health/backup/regression coverage was incomplete. |
| 2 | PARTIAL | Catalog existed, but authoritative TelDrive corpus discovery/ingestion was incomplete. R1 supplied the missing path. |
| 3 | FOUNDATION COMPLETE | Durable JobStore/lease/retry primitives existed, but the full executor model was not complete. R4 supplied the reconciliation. |
| 4 | PARTIAL | Local transfer was proven; rclone was an adapter/dry-run boundary rather than a complete backend. R4 reconciled the durable execution boundary. |
| 5 | PARTIAL | Deterministic planner/executor existed, but normal durable workflow integration was incomplete. R4 reconciled the execution path. |
| 6 | PARTIAL | Archive engine was strong, but the documented workflow was not fully integrated. R4 reconciled the durable execution boundary. |
| 7 | COMPLETE (core) | Integrity evidence and duplicate grouping were implemented and host-gated without production mutation. |
| 8 | PARTIAL | Lifecycle primitives existed but CLI exposure and physical/logical terminal-state reconciliation were incomplete. |
| 9 | PARTIAL | Backup scheduling existed, but a complete backup executor path was missing. R4 reconciled durable execution. |
| 10 | PARTIAL | Monitoring existed, but the full operational notification/health model was incomplete. |
| 11 | PARTIAL | CLI exposed many Lab operations, but documentation and implementation surfaces did not fully match. |
| 12 | PRIMITIVES | Storage/cache intelligence was implemented as local primitives, not yet a proven end-to-end product workflow. |
| 13 | PRIMITIVES | Read-only interoperability existed, but boundary hardening and integration evidence remained. |
| 14 | INCOMPLETE | Jellyfin/OTT was not operational at R0; R3 later supplied the operational media/playback evidence. |
| 15 | PROVIDER PRIMITIVES | OCR/STT/embedding/visual helpers existed, but provider integration and semantic quality were not established as a product pipeline. |
| 16 | INCOMPLETE | Advanced content search was separate from `td search`; authoritative corpus ingestion and unified search were missing. R2 later reconciled the core search surface. |
| 17 | ADVISORY PRIMITIVES | AI assistance was advisory, but product integration and end-to-end value were not complete. |
| 18 | ADVISORY | Storage analytics/recommendation primitives existed; operational integration remained incomplete. |
| 19 | SNAPSHOT PRIMITIVES | Snapshot/restore primitives existed, but the complete durable operational workflow was not proven. |
| 20 | CONTRACTS | Cross-project contracts existed; production integrations were not yet operational workflows. |
| 21 | EXPERIMENTAL | Experimental primitives existed and had to remain isolated until proven. |
| 22 | INCOMPLETE | Control Center was a UI/API shell with default empty payloads rather than a live control-plane surface. R5 later supplied the live read-only surface. |

## Historical critical product gaps

These were the R0 gaps that drove the subsequent reconciliation sequence:

### 1. Corpus discovery

The Lab needed automatic discovery of the existing TelDrive corpus through an authoritative, bounded, incremental metadata interface. R1 delivered that path.

### 2. TD Search

The intended search surface was:

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

R2 reconciled the core unified search surface. Optional content providers remain capability-gated.

### 3. Media/OTT

The R0 target workflow was:

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

R3 later supplied real library indexing/playback and protection evidence using disposable Lab-owned media.

## R0 cleanup rules — enduring safety rules

1. Do not start new feature phases merely to avoid fixing existing integration gaps.
2. Do not call adapters, contracts, mocks, or shallow capability tests end-to-end features.
3. Keep production TelDrive storage and database outside Lab ownership.
4. Keep the ₹0 constraint: no paid runtime dependency, paid API, or mandatory remote AI.
5. Prefer one canonical implementation over duplicate implementations or overlapping retry/error systems.
6. Make resource-sensitive operations streaming/bounded where practical.
7. Non-loopback read-only APIs require explicit security controls; localhost remains the safe default.
8. Lab runtime state/cache paths must be rejected if they resolve inside protected production roots.
9. Caller-issued authorization must remain separate from planning/execution.
10. Release claims must be evidence-driven.

## R1–R6 reconciliation record

### R1 — Corpus Discovery

**Status: COMPLETE.** Bounded authoritative rclone metadata discovery, catalog ingestion, stable provenance, idempotence, and stale-path reporting were implemented and gated without production mutation.

### R2 — Unified TD Search

**Status: COMPLETE.** `td search` was reconciled around the discovered corpus with SQLite FTS5 and bounded/read-only search behavior. Optional content/semantic providers remain capability-gated.

### R3 — Operational Media/OTT

**Status: COMPLETE.** Real Jellyfin 12.0 library indexing/playback, controlled read-only exposure, protection, and verification were proven with disposable Lab-owned media.

### R4 — Durable Execution Reconciliation

**Status: COMPLETE.** JobStore, Worker, TransferManager, rclone, Archive, Organization, Backup, Lifecycle, Verification, and Audit were reconciled around durable execution, recovery, fencing, and evidence.

### R5 — Live Control Center

**Status: COMPLETE.** The Control Center is loopback-only, GET-only, and backed by live catalog/jobs/transfers/media/search/health/audit/config state.

### R6 — Production Hardening / Release

**Status: COMPLETE as a hardening gate.** Safety, zero-cost, least-privilege CI, production-boundary, unsafe-shell, complete gate-matrix, and evidence-controlled-claim checks pass. A final release tag remains governed by the current release checklist and clean-worktree requirements.

## Current status pointer

For the current project status, do not use the historical R0 table above. Use:

1. `ROADMAP.md` — canonical current roadmap/status.
2. `docs/PHASES_12_22_IMPLEMENTATION_STATUS.md` — current Phase 12–22 evidence scope.
3. R1–R6 completion documents — detailed reconciliation evidence.
4. `docs/RELEASE_CHECKLIST.md` — release-control state.

The project now distinguishes two claims that must not be conflated:

- **Core control-plane completion:** reconciled and release-hardened through R6.
- **Optional/experimental extension evidence:** implemented where documented, but not every P12–P21 capability has independent real-world E2E evidence.

That distinction is intentional and is part of the product's evidence standard.
