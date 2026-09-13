# TelDrive Lab Roadmap

This is the canonical implementation roadmap for TelDrive Lab. It is ordered by dependency and safety, not by feature excitement.

> **Product truth:** TelDrive remains the production storage authority. TelDrive Lab is the safe engineering control plane around it.

## Completion standard

A phase or capability is not `COMPLETE` merely because code, tests, an adapter, or a contract exists.

```text
PRIMITIVE → IMPLEMENTED → INTEGRATED → OPERATIONAL → END-TO-END VERIFIED → DOCUMENTED → COMPLETE
```

See `docs/RECONCILIATION_GATE_R0.md` for the evidence-based status and the R0→R5 reconciliation program.

---

# Phase 0 — Lab Foundation

**Goal:** establish the sidecar control plane without taking ownership of existing storage.

- repository and runtime separation
- explicit protected production boundary
- policy, authorization, job, transfer, catalog, verification, audit, and monitoring architecture
- testable safety invariants

**Status at R0:** COMPLETE.

---

# Phase 1 — Reliability & Safety Foundation

**Goal:** observe, protect, back up, and recover the existing environment without silently repairing production.

- Recent regression protection (`Recent → createdAt`, not `updatedAt`)
- secret-free configuration references/backups
- database backup and isolated restore validation
- mount/service health for TelDrive, PostgreSQL, Docker, rclone, FUSE, and storage roots
- RAM/CPU/disk/network/process monitoring

**Status at R0:** PARTIAL.

---

# Phase 2 — Metadata & Index Foundation

**Goal:** build a rebuildable local catalog without becoming a second source of truth.

- canonical `FileRecord`
- SQLite derived catalog
- bounded incremental discovery/ingestion from authoritative interfaces
- filename/path search and FTS preparation
- smart views
- SHA-256 hash index and verification state

**Status at R0:** PARTIAL. The catalog exists, but authoritative TelDrive corpus discovery/ingestion is not yet complete. This is the R1 dependency.

---

# Phase 3 — Durable Job Engine

**Goal:** replace fragile one-off automation with durable, restart-safe execution.

Core job types include `UPLOAD`, `DOWNLOAD`, `ARCHIVE`, `VERIFY`, `BACKUP`, `SNAPSHOT`, `ORGANIZE`, `CLEANUP`, `INDEX`, and `RESTORE`.

Required states:

```text
QUEUED → RUNNING → VERIFYING → COMPLETED
             ├→ PAUSED → QUEUED
             ├→ FAILED
             └→ CANCELLED
```

Required properties include durable timestamps/progress, leases, bounded retries, classified failures, parent/child jobs, explicit authorization, safe cancellation, and auditability.

**Status at R0:** FOUNDATION COMPLETE. The JobStore/lease/retry foundation exists, but the full executor model is reconciled later in R4.

---

# Phase 4 — Transfer Manager

**Goal:** create one controlled transfer boundary for future workflows.

Backends:

```text
Local filesystem
rclone
future controlled backends
```

Required properties include explicit source/destination, dry-run, authorization, progress, bounded concurrency, retries, checksum verification, failure classification, reconciliation, and no arbitrary shell execution.

The initial rclone boundary is intentionally narrow: controlled `rclone copyto` only; no config rewriting, remounting, or service reconfiguration.

**Status at R0:** PARTIAL. Local transfer and the dry-run rclone boundary are proven. A complete production rclone backend is not yet integrated.

---

# Phase 5 — Deterministic Organization Engine

**Goal:** make organization predictable, policy-driven, and reviewable.

```text
td organize --dry-run
        ↓
review plan
        ↓
explicit authorization
        ↓
controlled execution
        ↓
verify
        ↓
audit
```

AI is never the organization authority.

**Status at R0:** PARTIAL. Deterministic planning/execution is proven in isolation; durable workflow, catalog, and audit integration remain for reconciliation.

---

# Phase 6 — Archive Manager

**Goal:** turn archival into a safe, composable one-way workflow.

Canonical flow:

```text
DISCOVER → HASH → DUPLICATE CHECK → POLICY → DRY-RUN → AUTHORIZATION
→ QUEUE → TRANSFER → VERIFY → INDEX → AUDIT
```

Initial archival is local → TelDrive. Local source deletion and two-way synchronization are not part of the default workflow.

**Status at R0:** PARTIAL, not COMPLETE. The archive engine and durable adapter exist, but the CLI path does not yet fully connect catalog-wide duplicate detection, durable queue execution, destination indexing, and audit recording into the documented end-to-end workflow. R4 reconciles the execution path.

---

# Phase 7 — Integrity & Duplicate Intelligence

**Goal:** know whether copies are trustworthy and identify duplicates without destructive automation.

- SHA-256 checksum evidence
- duplicate groups by checksum + size
- verification and stale/missing-copy reporting
- report-only duplicate handling

```text
DUPLICATE FOUND ≠ DELETE
```

**Status at R0:** CORE COMPLETE. The core integrity/duplicate evidence path is host-gated without production mutation.

---

# Phase 8 — Safety & Lifecycle Management

**Goal:** make cleanup possible without making accidental destruction easy.

- quarantine/trash
- safety window and retention policy
- explicit purge
- protected-path enforcement
- cleanup verification
- lifecycle audit trail

**Status at R0:** PARTIAL. Lifecycle primitives exist; complete CLI exposure and physical/logical terminal-state reconciliation remain.

---

# Phase 9 — Scheduled Backups & Snapshots

**Goal:** automate proven backup workflows through the durable Job Engine.

```text
schedule → snapshot/backup → checksum → archive → verify → retention
```

**Status at R0:** PARTIAL. Scheduling can create durable backup jobs, but a complete backup executor path is not yet present.

---

# Phase 10 — Monitoring & Notifications

**Goal:** know what the Lab is doing without constantly watching it.

Monitor service health, job health, throughput, queue depth, failures, disk/cache use, RAM pressure, network failures, and integrity failures. Prefer local/free notifications.

**Status at R0:** PARTIAL.

---

# Phase 11 — CLI

**Goal:** make the Lab controllable from the terminal without requiring a web UI.

Current control surfaces include status, health, search, index, jobs, job control, audit, monitoring, organization, archive, verification, lifecycle, and backup scheduling. The CLI must expose plans, dry-runs, authorization boundaries, job state, verification, and audit information.

**Status at R0:** PARTIAL. Documentation and implementation surfaces still require reconciliation.

---

# Phase 12 — Smart Storage & Cache Intelligence

**Goal:** make local cache behavior predictable and resource-aware.

Hot/cold classification, access frequency, cache pressure, prefetch suggestions, eviction planning, resource-aware transfers, and RAM-aware concurrency. No automatic production eviction.

**Status at R0:** PRIMITIVES.

---

# Phase 13 — Read-only Interoperability

**Goal:** expose safe metadata interfaces without changing TelDrive.

Read-only JSON/IPC metadata surfaces and catalog export/import are optional interfaces. No TelDrive database write access.

**Status at R0:** PRIMITIVES.

---

# Phase 14 — Media Ecosystem

**Goal:** build an operational media-aware workflow around the archive.

Target outcome:

```text
TelDrive corpus → automatic media discovery → media catalog
→ Jellyfin library exposure → Jellyfin → actual playback
```

**Status at R3:** COMPLETE. The isolated R3 reconciliation gate now verifies bounded discovery/classification, controlled read-only exposure, real Jellyfin 12.0 startup/authentication, real library indexing, real stream playback, read-only container protection, and absence of TelDrive production mutation. See `docs/R3-MEDIA-JELLYFIN.md`.

---

# Phase 15 — Media & Document Intelligence

**Goal:** understand stored content using free/local tooling where practical.

Possible tools include OCR, PDF metadata, document classification, local speech-to-text, local embeddings, and local vision. AI remains advisory.

**Status at R0:** PROVIDER PRIMITIVES. Provider availability and integrated indexing quality must be proven before claiming product completion.

---

# Phase 16 — Advanced Search

**Goal:** move from filename search toward content-aware discovery.

```text
filename/path → metadata → full text → OCR/transcript → embeddings → semantic search
```

**Status at R0:** INCOMPLETE. Advanced content search is separate from `td search`; R2 unifies the product surface.

---

# Phase 17 — Optional Local AI

**Goal:** add AI assistance without making AI authoritative.

Natural-language search, archive/organization suggestions, duplicate/anomaly explanation, media classification, and metadata enrichment are advisory only.

**Status at R0:** ADVISORY PRIMITIVES.

---

# Phase 18 — Storage Intelligence

**Goal:** understand storage economics and behavior without paid services.

Growth forecasting, heatmaps, category analysis, reclaim estimates, archive recommendations, and transfer-cost estimation remain advisory.

**Status at R0:** ADVISORY.

---

# Phase 19 — Time Machine / Snapshot System

**Goal:** provide durable point-in-time recovery workflows.

Snapshot manifests, incremental snapshots, retention, verification, restore planning/dry-runs, and explicit restore authorization. Restore is high-risk.

**Status at R0:** SNAPSHOT PRIMITIVES.

---

# Phase 20 — Cross-Project Integrations

**Goal:** allow other engineering projects to consume Lab capabilities safely through explicit contracts.

Potential consumers include VAJRA, Alok Engineering Lab, local development environments, datasets, and experiment archives.

**Status at R0:** CONTRACTS.

---

# Phase 21 — Advanced / Experimental

Potential experiments include content-addressable storage, deduplication optimization, intelligent tiering, snapshot compression, distributed workers, remote workers, and advanced local AI orchestration.

**Status at R0:** EXPERIMENTAL. Experimental features remain isolated until proven.

---

# Phase 22 — Optional Storage Control Center

**Goal:** provide a local UI over an already-proven control plane.

Possible surfaces include dashboard, jobs, transfers, archive plans, search, storage analytics, health, audit, and configuration visibility.

**Status at R5:** COMPLETE. The historical shell/default payload was reconciled into the live, loopback-only, read-only Control Center backed by Lab-owned catalog, durable jobs, media, search, health, audit, and configuration state. See `docs/R5-LIVE-CONTROL-CENTER.md`.

---

# Reconciliation Program — R0 → R5

The numbered implementation phases above describe capability history and intended dependencies. The following gates reconcile the product before new feature expansion.

```text
R0 Product Truth
      ↓
R1 Corpus Discovery
      ↓
R2 Unified TD Search
      ↓
R3 Operational Media / OTT
      ↓
R4 Durable Execution Reconciliation
      ↓
R5 Live Control Center
```

### R0 — Product Truth

Make roadmap, documentation, code, tests, host gates, CI, and release claims agree with actual evidence. Remove false completion claims, resolve safety/documentation contradictions, consolidate duplicate implementation concepts, and establish evidence-driven CI.

### R1 — Corpus Discovery

Build authoritative, bounded, incremental TelDrive metadata discovery/ingestion into the derived catalog. Preserve provenance and idempotence. Existing TelDrive files must not require manual registration.

### R2 — Unified TD Search

Make `td search` operate over the discovered corpus and unify filename/path, metadata, media metadata, full text, OCR/transcripts, and optional semantic indexes.

### R3 — Operational Media / OTT

Build and verify TelDrive corpus → media discovery → media catalog → Jellyfin library exposure → actual playback using safe Lab-owned/test media.

**Status:** COMPLETE. The R3 CI gate verifies DISCOVER → CLASSIFY → EXPOSE → SERVE → INDEX → PLAY → PROTECT → VERIFY, and the workflow is documented. The automated path uses only disposable Lab-owned media and never mutates production TelDrive/rclone state.

### R4 — Durable Execution Reconciliation

Unify JobStore, Worker, TransferManager, rclone, Archive, Organization, Backup, Lifecycle, Verification, and Audit. Progress and `VERIFYING` must be real persisted execution states, not merely modeled fields.

### R5 — Live Control Center

Wire the control center to live catalog, jobs, transfers, media, search, health, and audit state only after those underlying workflows are operational.

**Status:** COMPLETE. R5 is implemented, integrated into the CLI/CI, covered by unit/integration tests and a disposable host gate, and documented. The Control Center remains read-only and is not a mutation authority.

---

# Global Implementation Gates

Every phase/capability must pass the applicable evidence gates:

1. Design review
2. Unit tests
3. Integration tests
4. Safety tests
5. Failure-path tests
6. Host gate
7. Resource check
8. Audit check
9. Documentation
10. Git checkpoint

No feature is complete merely because a local happy-path test passes.

# Global Safety / Cost Invariants

- TelDrive remains the storage authority.
- Existing production storage and database remain outside Lab ownership.
- No direct TelDrive PostgreSQL writes.
- No autonomous destructive production cleanup.
- No silent production mutation.
- AI/planners/UIs/schedulers are never mutation authority.
- Mutation requires deterministic policy, explicit authorization, controlled execution, verification, and audit.
- ₹0/$0 remains mandatory: no paid runtime dependency, paid API, or mandatory remote AI.
- Optional ecosystems may be unavailable, but adapters must never be described as operational proof.
- Resource-sensitive operations should be bounded and streaming where practical.
