# TelDrive Lab Roadmap

This is the canonical implementation roadmap for TelDrive Lab. It is ordered by dependency and safety, not by feature excitement.

> **Product truth:** TelDrive remains the production storage authority. TelDrive Lab is the safe engineering control plane around it.

## Completion standard

A phase or capability is not `COMPLETE` merely because code, tests, an adapter, or a contract exists.

```text
PRIMITIVE → IMPLEMENTED → INTEGRATED → OPERATIONAL → END-TO-END VERIFIED → DOCUMENTED → COMPLETE
```

The R0 table below is a historical baseline. Current status is recorded in **Current status at R6** and in the R1–R6 reconciliation documents.

---

# Current status at R6

R6 is the current release-hardening checkpoint. The core TelDrive Lab control plane is complete and release-hardened through R0–R6. Phases 12–21 contain implemented optional/advisory/experimental extensions; their implementation is not equivalent to universal real-world end-to-end verification. Phase 22 is a read-only live Control Center surface, with storage analytics and archive/search represented as control-plane payload/API surfaces rather than an independent destructive workflow UI.

| Area | Current status | Evidence / interpretation |
|---|---|---|
| R0 Product Truth | COMPLETE | Repository/CI reconciliation, safety boundaries, evidence-controlled claims. |
| R1 Corpus Discovery | COMPLETE | Bounded authoritative rclone metadata discovery, catalog ingestion, idempotence, stale-path reporting, tests and host gate. |
| R2 Unified TD Search | COMPLETE | `td search`, FTS5, derived-index synchronization, filters, pagination and read-only contract. |
| R3 Media / OTT | COMPLETE | Real Jellyfin 12.0 library indexing and playback with disposable Lab-owned media, read-only protection and host/CI evidence. |
| R4 Durable Execution | COMPLETE | Durable JobStore/Worker/TransferManager execution, leases, verification state, recovery/fencing and audit evidence. |
| R5 Live Control Center | COMPLETE | Loopback-only, GET-only Control Center backed by live catalog/jobs/transfers/media/search/health/audit/config state. |
| R6 Release Hardening | COMPLETE | Zero-cost, least-privilege, production-boundary, unsafe-shell, CI-matrix and evidence-controlled release gates pass. Final release decision remains subject to clean working tree/release checklist conditions. |
| Phases 0–11 | COMPLETE at reconciled control-plane level | R0–R4 reconciliation superseded the old R0-era partial labels; see individual R1–R4 evidence documents. |
| Phase 12 | IMPLEMENTED / capability-gated | Deterministic storage/cache intelligence is implemented and tested; no automatic production eviction. Not independently E2E-proven as a universal product workflow. |
| Phase 13 | IMPLEMENTED / read-only | JSON/IPC/metadata export-import surfaces are implemented and tested; optional interfaces remain bounded/read-only. |
| Phase 14 | COMPLETE | Superseded by the stronger R3 operational media/Jellyfin evidence. |
| Phase 15 | IMPLEMENTED / optional providers | OCR/PDF/STT/embedding/vision capabilities exist with optional local providers; provider availability and semantic quality are not universal E2E claims. |
| Phase 16 | IMPLEMENTED / capability-gated | Content-aware indexing/search and semantic ranking exist; not every provider/content modality has independent real-world E2E evidence. |
| Phase 17 | ADVISORY / implemented | Local AI assistance is advisory and policy-bounded; it is never mutation authority and is not claimed as a universally operational AI product. |
| Phase 18 | IMPLEMENTED / advisory | Storage analytics and recommendations are deterministic/advisory; no destructive automation is implied. |
| Phase 19 | IMPLEMENTED / high-risk workflow primitives | Snapshot, retention, verification and restore planning/dry-run are implemented; restore remains explicitly authorized and is not claimed as independently production E2E-proven. |
| Phase 20 | CONTRACTS / implemented | Explicit cross-project contracts exist; consuming projects are not represented as independently production-integrated workflows. |
| Phase 21 | EXPERIMENTAL / implemented | CAS, dedup planning, tiering, compression, worker and local-AI orchestration capabilities remain isolated/advisory until separately proven. |
| Phase 22 | COMPLETE as read-only Control Center surface | Live dashboard/control-plane API is operational; storage analytics and archive/search are exposed as payload/control surfaces, not an autonomous mutation UI. |

### What “complete” means here

The **core product** is the reconciled control plane: safe observation, catalog discovery, search, media serving, durable execution, live control-center visibility, verification, audit, and release hardening. This core has the required integration/operational/E2E evidence through R0–R6.

The Phase 12–21 extension layer is **implemented**, but optional providers, advisory features, experimental workers, and high-risk restore workflows are not promoted to universal `COMPLETE` merely because deterministic local tests exist. Their status is intentionally capability-gated and evidence-scoped.

Therefore this roadmap does **not** claim that every optional P12–P21 capability has independent real-world E2E evidence. That is a deliberate accuracy boundary, not an unfinished feature phase.

---

# Phase 0 — Lab Foundation

**Goal:** establish the sidecar control plane without taking ownership of existing storage.

- repository and runtime separation
- explicit protected production boundary
- policy, authorization, job, transfer, catalog, verification, audit, and monitoring architecture
- testable safety invariants

**Historical R0 status:** COMPLETE.

---

# Phase 1 — Reliability & Safety Foundation

**Goal:** observe, protect, back up, and recover the existing environment without silently repairing production.

- Recent regression protection (`Recent → createdAt`, not `updatedAt`)
- secret-free configuration references/backups
- database backup and isolated restore validation
- mount/service health for TelDrive, PostgreSQL, Docker, rclone, FUSE, and storage roots
- RAM/CPU/disk/network/process monitoring

**Current status:** COMPLETE at reconciled control-plane level; the old R0 `PARTIAL` label is historical.

---

# Phase 2 — Metadata & Index Foundation

**Goal:** build a rebuildable local catalog without becoming a second source of truth.

- canonical `FileRecord`
- SQLite derived catalog
- bounded incremental discovery/ingestion from authoritative interfaces
- filename/path search and FTS preparation
- smart views
- SHA-256 hash index and verification state

**Current status:** COMPLETE at reconciled control-plane level through R1/R2. The old R0 `PARTIAL` label is historical.

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

**Current status:** COMPLETE through R4 durable-execution reconciliation. The old R0 `FOUNDATION COMPLETE` label is historical.

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

**Current status:** COMPLETE at reconciled control-plane level through R4. The old R0 `PARTIAL` label is historical.

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

**Current status:** COMPLETE at reconciled control-plane level through R4. The old R0 `PARTIAL` label is historical.

---

# Phase 6 — Archive Manager

**Goal:** turn archival into a safe, composable one-way workflow.

Canonical flow:

```text
DISCOVER → HASH → DUPLICATE CHECK → POLICY → DRY-RUN → AUTHORIZATION
→ QUEUE → TRANSFER → VERIFY → INDEX → AUDIT
```

Initial archival is local → TelDrive. Local source deletion and two-way synchronization are not part of the default workflow.

**Current status:** COMPLETE at reconciled control-plane level through R4 durable execution. The old R0 `PARTIAL` label is historical.

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

**Current status:** COMPLETE. Core integrity/duplicate evidence is host-gated without production mutation.

---

# Phase 8 — Safety & Lifecycle Management

**Goal:** make cleanup possible without making accidental destruction easy.

- quarantine/trash
- safety window and retention policy
- explicit purge
- protected-path enforcement
- cleanup verification
- lifecycle audit trail

**Current status:** COMPLETE at reconciled control-plane level through R4. Any destructive production action remains authorization-gated and outside default automation.

---

# Phase 9 — Scheduled Backups & Snapshots

**Goal:** automate proven backup workflows through the durable Job Engine.

```text
schedule → snapshot/backup → checksum → archive → verify → retention
```

**Current status:** COMPLETE at reconciled control-plane level through R4; scheduling and durable execution are covered by the reconciled execution model. Production mutation remains protected.

---

# Phase 10 — Monitoring & Notifications

**Goal:** know what the Lab is doing without constantly watching it.

Monitor service health, job health, throughput, queue depth, failures, disk/cache use, RAM pressure, network failures, and integrity failures. Prefer local/free notifications.

**Current status:** COMPLETE at reconciled control-plane level. Health/resource visibility is also surfaced through R5. Optional notification ecosystems remain capability-gated.

---

# Phase 11 — CLI

**Goal:** make the Lab controllable from the terminal without requiring a web UI.

Current control surfaces include status, health, search, index, jobs, job control, audit, monitoring, organization, archive, verification, lifecycle, and backup scheduling. The CLI must expose plans, dry-runs, authorization boundaries, job state, verification, and audit information.

**Current status:** COMPLETE at reconciled control-plane level. The old R0 `PARTIAL` label is historical.

---

# Phase 12 — Smart Storage & Cache Intelligence

**Goal:** make local cache behavior predictable and resource-aware.

Hot/cold classification, access frequency, cache pressure, prefetch suggestions, eviction planning, resource-aware transfers, and RAM-aware concurrency. No automatic production eviction.

**Current status:** IMPLEMENTED / CAPABILITY-GATED. Deterministic local implementation and tests exist; universal real-world E2E is intentionally not claimed.

---

# Phase 13 — Read-only Interoperability

**Goal:** expose safe metadata interfaces without changing TelDrive.

Read-only JSON/IPC metadata surfaces and catalog export/import are optional interfaces. No TelDrive database write access.

**Current status:** IMPLEMENTED / READ-ONLY. Local tests and safety boundaries exist; external interoperability remains capability-gated.

---

# Phase 14 — Media Ecosystem

**Goal:** build an operational media-aware workflow around the archive.

Target outcome:

```text
TelDrive corpus → automatic media discovery → media catalog
→ Jellyfin library exposure → Jellyfin → actual playback
```

**Current status:** COMPLETE through R3. Real Jellyfin library indexing/playback and read-only protection were verified with disposable Lab-owned media.

---

# Phase 15 — Media & Document Intelligence

**Goal:** understand stored content using free/local tooling where practical.

Possible tools include OCR, PDF metadata, document classification, local speech-to-text, local embeddings, and local vision. AI remains advisory.

**Current status:** IMPLEMENTED / OPTIONAL PROVIDERS. Deterministic/local adapters exist, but provider availability, model quality, and complete provider-specific pipelines are not universal E2E claims.

---

# Phase 16 — Advanced Search

**Goal:** move from filename search toward content-aware discovery.

```text
filename/path → metadata → full text → OCR/transcript → embeddings → semantic search
```

**Current status:** IMPLEMENTED / CAPABILITY-GATED. Content indexing and semantic ranking exist; not every optional content provider/modality has independent real-world E2E evidence.

---

# Phase 17 — Optional Local AI

**Goal:** add AI assistance without making AI authoritative.

Natural-language search, archive/organization suggestions, duplicate/anomaly explanation, media classification, and metadata enrichment are advisory only.

**Current status:** ADVISORY / IMPLEMENTED. Local model capability detection and advisory wrappers exist. AI is never mutation authority and universal AI-provider E2E is not claimed.

---

# Phase 18 — Storage Intelligence

**Goal:** understand storage economics and behavior without paid services.

Growth forecasting, heatmaps, category analysis, reclaim estimates, archive recommendations, and transfer-cost estimation remain advisory.

**Current status:** IMPLEMENTED / ADVISORY. Deterministic analytics and recommendation primitives are covered by local tests; destructive reclaim is not automatic.

---

# Phase 19 — Time Machine / Snapshot System

**Goal:** provide durable point-in-time recovery workflows.

Snapshot manifests, incremental snapshots, retention, verification, restore planning/dry-runs, and explicit restore authorization. Restore is high-risk.

**Current status:** IMPLEMENTED / HIGH-RISK, CAPABILITY-GATED. Snapshot and restore-planning primitives are tested; production restore is never implied by a dry-run or adapter.

---

# Phase 20 — Cross-Project Integrations

**Goal:** allow other engineering projects to consume Lab capabilities safely through explicit contracts.

Potential consumers include VAJRA, Alok Engineering Lab, local development environments, datasets, and experiment archives.

**Current status:** CONTRACTS / IMPLEMENTED. Explicit versioned contracts exist; independent production integrations are not claimed.

---

# Phase 21 — Advanced / Experimental

Potential experiments include content-addressable storage, deduplication optimization, intelligent tiering, snapshot compression, distributed workers, remote workers, and advanced local AI orchestration.

**Current status:** EXPERIMENTAL / IMPLEMENTED. Capabilities exist behind Lab-owned boundaries and remain isolated/advisory until separately proven for a concrete workflow.

---

# Phase 22 — Optional Storage Control Center

**Goal:** provide a local UI over an already-proven control plane.

Surfaces include dashboard, jobs, transfers, archive/search payloads, storage analytics, health, audit, and configuration visibility.

**Current status:** COMPLETE as a read-only live Control Center through R5. It is loopback-only and GET-only, backed by live Lab state. Storage analytics and archive/search are documented as control-plane payload/API surfaces; the Control Center is not a mutation authority.

---

# Reconciliation Program — R0 → R6

The numbered implementation phases above describe capability history and intended dependencies. The following gates reconciled the core product before release hardening.

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
      ↓
R6 Production Hardening / Release
```

### R0 — Product Truth

Reconcile roadmap, documentation, code, tests, host gates, CI, and release claims with actual evidence.

### R1 — Corpus Discovery

Build authoritative, bounded, incremental TelDrive metadata discovery/ingestion into the derived catalog. Preserve provenance and idempotence.

**Status:** COMPLETE.

### R2 — Unified TD Search

Make `td search` operate over the discovered corpus and unify applicable filename/path, metadata, media metadata, full text, OCR/transcripts, and optional semantic indexes.

**Status:** COMPLETE for the supported deterministic search stack. Optional providers remain capability-gated.

### R3 — Operational Media / OTT

Build and verify TelDrive corpus → media discovery → media catalog → Jellyfin library exposure → actual playback using safe Lab-owned/test media.

**Status:** COMPLETE. The R3 CI/host evidence verifies DISCOVER → CLASSIFY → EXPOSE → SERVE → INDEX → PLAY → PROTECT → VERIFY.

### R4 — Durable Execution Reconciliation

Unify JobStore, Worker, TransferManager, rclone, Archive, Organization, Backup, Lifecycle, Verification, and Audit behind the durable execution boundary.

**Status:** COMPLETE.

### R5 — Live Control Center

Wire the Control Center to live catalog, jobs, transfers, media, search, health, and audit state only after those underlying workflows are operational.

**Status:** COMPLETE. The Control Center is read-only and is not a mutation authority.

### R6 — Production Hardening / Release

Run the final safety, CI, dependency, boundary, documentation, and target-host checks and make an evidence-controlled release decision.

**Status:** COMPLETE as a hardening gate. A release tag remains subject to the release checklist's final clean-worktree and release-note conditions.

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
