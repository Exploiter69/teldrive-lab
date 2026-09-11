# TelDrive Lab Roadmap

This is the canonical implementation roadmap for TelDrive Lab. It is ordered by dependency and safety, not by feature excitement.

---

# Phase 0 — Lab Foundation

**Goal:** establish the sidecar control plane without taking ownership of existing storage.

## 0.1 Repository and runtime separation

- source code lives in `~/teldrive-lab`
- runtime state lives in `~/.local/share/teldrive-lab/`
- cache lives in `~/.cache/teldrive-lab/`
- existing TelDrive data and state remain outside the Lab repository

## 0.2 Core architecture

```text
                    ┌───────────────────────┐
                    │       TelDrive        │
                    │  existing authority   │
                    └──────────┬────────────┘
                               │
                        supported interfaces
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                       TelDrive Lab                           │
│                                                              │
│  CLI                                                         │
│   │                                                          │
│   ▼                                                          │
│  Policy Engine ────────► Authorization                       │
│   │                         │                                │
│   ▼                         ▼                                │
│  Job Engine ─────────► Transfer Manager                      │
│   │                         │                                │
│   ▼                         ▼                                │
│  Catalog / Index ◄──── Verification                           │
│   │                                                          │
│   ▼                                                          │
│  Audit / Monitoring                                           │
└──────────────────────────────────────────────────────────────┘
```

## 0.3 Product principle

TelDrive remains the storage authority. TelDrive Lab is a safe automation, indexing, verification, organization, archive, backup, monitoring, and intelligence layer around it.

The Lab must never silently become the owner of production storage.

### Exit criteria

- architecture documents are internally consistent
- protected production boundary is explicit
- no implementation assumes ownership of existing storage
- safety invariants are testable
- runtime state is outside the repository

---

# Phase 1 — Reliability & Safety Foundation

**Goal:** prove that the Lab can observe, protect, back up, and recover the existing environment before introducing durable automation.

## 1.1 Recent regression protection

Preserve the existing invariant:

```text
Recent → createdAt
```

not `updatedAt`.

Create a repeatable compatibility/regression check so future Lab or upstream work cannot silently regress the behavior.

## 1.2 Safe configuration backup

Create versioned, secret-free templates/references for:

- TelDrive configuration
- rclone service definitions/configuration references
- systemd units
- Docker configuration
- Lab configuration

Never commit secrets, session material, tokens, or private production state.

## 1.3 Database backup and isolated restore

Build and test:

```text
backup
 ↓
verify backup exists
 ↓
restore into isolated test location
 ↓
validate
```

A backup that has never been restored is not considered proven.

## 1.4 Mount and service health

Observe:

- `~/TelegramRaw`
- `~/TelegramDrive`
- FUSE health
- read/write accessibility where safe
- stale mount conditions
- rclone systemd state
- TelDrive
- PostgreSQL
- Docker

Health monitoring must not silently repair or mutate production.

## 1.5 Resource monitoring

Track:

- RAM
- CPU
- disk capacity
- disk I/O
- network reachability
- rclone processes

---

# Phase 2 — Metadata & Index Foundation

**Goal:** build a rebuildable local catalog without becoming a second source of truth.

## 2.1 Canonical file model

The Lab uses a canonical `FileRecord` with provenance, source identity, destination identity, checksum state, verification state, and lifecycle metadata.

## 2.2 SQLite catalog

Use:

```text
~/.local/share/teldrive-lab/catalog.db
```

The catalog is derived, rebuildable state. Losing it must not mean losing storage data.

## 2.3 Discovery and ingestion

Implement bounded, incremental discovery from authoritative interfaces such as local filesystems and safely available TelDrive/rclone metadata.

## 2.4 Search foundation

Start with filename/path search and prepare SQLite FTS for later content search.

Example concepts:

```text
td search "VAJRA"
td search "quantum transformer"
td search "*.pdf"
```

## 2.5 Smart views

Examples:

- large files
- recent files
- unverified
- archives
- datasets
- encrypted
- movies
- backups
- duplicates
- never accessed

These are query views, not physical storage reorganization.

## 2.6 Hash index

Use SHA-256 initially. Store hash, size, provenance, source/Telegram identity where available, and verification state. Benchmark BLAKE3 later before changing the canonical choice.

### Phase 2 exit gate

- catalog can be rebuilt from authoritative sources
- indexing is incremental and bounded
- deterministic hashes work
- metadata search works
- catalog corruption cannot corrupt production storage

**Hard dependency:** Phase 2 must pass before Phase 3 Job Engine implementation.

---

# Phase 3 — Durable Job Engine

**Goal:** replace fragile one-off automation with durable, restart-safe execution.

### Core job types

```text
UPLOAD
DOWNLOAD
ARCHIVE
VERIFY
BACKUP
SNAPSHOT
ORGANIZE
CLEANUP
INDEX
RESTORE
```

### Required fields

```text
job_id
type
priority
state
created_at
started_at
updated_at
completed_at
attempts
max_attempts
retry_at
source
destination
path
size
checksum
progress
error_code
error_message
worker_id
lease_until
parent_job_id
```

### States

```text
QUEUED
RUNNING
PAUSED
VERIFYING
COMPLETED
FAILED
CANCELLED
```

### Normal flow

```text
QUEUED
  ↓
RUNNING
  ↓
VERIFYING
  ↓
COMPLETED
```

### Worker rules

- jobs survive process restarts
- leases prevent duplicate workers
- stale leases are recoverable
- retries are bounded
- retries use classified errors
- worker never self-authorizes
- destructive operations require explicit authorization
- every transition is auditable

### Exit criteria

- queue survives restart
- jobs can resume
- duplicate execution is prevented
- retry state is durable
- cancellation is safe
- parent/child jobs work
- audit records exist

---

# Phase 4 — Transfer Manager

**Goal:** create a single controlled transfer boundary for every future workflow.

### Transfer backends

```text
Local filesystem
rclone
future controlled backends
```

### Required properties

- explicit source and destination
- dry-run support
- authorization support
- progress reporting
- bounded concurrency
- bandwidth awareness
- retries
- checksum verification
- failure classification
- reconciliation
- atomic publication where possible
- no shell interpolation
- no hidden mount changes

### rclone boundary

Initial scope should be intentionally narrow:

```text
rclone copyto
```

with controlled arguments, no arbitrary shell commands, no config rewriting, no remounting, and no service reconfiguration.

### Exit criteria

- local transfer works
- rclone boundary works in dry-run mode
- checksum verification works
- protected production paths are blocked
- transfer failures are classified
- resource limits are enforced
- host gate passes without production mutation

---

# Phase 5 — Deterministic Organization Engine

**Goal:** make organization predictable, policy-driven, and reviewable.

### Classification inputs

- MIME type
- extension
- filename
- path
- size
- timestamps
- existing metadata
- explicit user rules

### Policy examples

```text
projects/** → encrypted
backups/** → encrypted
movies/** → raw
datasets/** → raw
```

### Workflow

```text
td organize --dry-run
        ↓
review plan
        ↓
explicit authorization
        ↓
td organize --apply
        ↓
verify
        ↓
audit
```

AI is not the organization authority. Deterministic policy decides whether and how a proposed classification is applied.

---

# Phase 6 — Archive Manager

**Goal:** turn archival into a safe, composable one-way workflow.

### Canonical flow

```text
DISCOVER
  ↓
HASH
  ↓
DUPLICATE CHECK
  ↓
POLICY EVALUATION
  ↓
DRY-RUN
  ↓
AUTHORIZATION
  ↓
QUEUE
  ↓
TRANSFER
  ↓
VERIFY
  ↓
INDEX
  ↓
AUDIT
```

Example:

```text
td archive <file>
```

### Archive watcher

A future staging directory such as `~/Archive/` may feed the same durable workflow:

```text
file appears
 ↓
watcher
 ↓
queue
 ↓
archive workflow
```

### Critical boundary

Initial archival is **local → TelDrive**. Local deletion/cleanup is not part of the default archive operation. Two-way synchronization is deferred.

### Implementation status

**COMPLETE — Phase 6 implementation is now present in the Lab.**

Implemented in `teldrive_lab/archive.py` and integrated with the Phase 4 transfer boundary:

- deterministic one-way local-source archive policy
- SHA-256 discovery
- informational duplicate detection
- conflict-safe no-overwrite planning
- protected production boundary enforcement
- stable archive-plan digest
- explicit authorization at apply time
- post-transfer verification
- durable `ARCHIVE` executor adapter
- CLI dry-run/apply workflow
- isolated Phase 6 host gate

No local source deletion is performed, and the host gate performs zero production storage mutation.

---

# Phase 7 — Integrity & Duplicate Intelligence

**Goal:** know whether copies are trustworthy and identify duplicates without destructive automation.

### Work

- SHA-256 checksum database
- duplicate groups by checksum + size
- upload verification
- download verification
- periodic verification
- stale checksum detection
- integrity reports
- missing verified-copy reports
- optional BLAKE3 benchmark

### Safety invariant

```text
DUPLICATE FOUND ≠ DELETE
```

The system may report potentially reclaimable space. Any destructive cleanup requires a separate explicit authorization workflow.

---

# Phase 8 — Safety & Lifecycle Management

**Goal:** make cleanup possible without making accidental destruction easy.

### Work

- quarantine/trash area
- safety window before purge
- retention policies
- explicit purge
- immutable/locked archive mode
- cleanup planner
- protected-path enforcement
- cleanup verification
- lifecycle audit trail

### Default

Uncertain or protected states stop the operation rather than causing the system to guess.

---

# Phase 9 — Scheduled Backups & Snapshots

**Goal:** automate proven backup workflows using the durable Job Engine.

### Flow

```text
schedule
 ↓
snapshot/backup
 ↓
checksum
 ↓
archive
 ↓
verify
 ↓
retention
```

---

# Phase 10 — Monitoring & Notifications

**Goal:** know what the Lab is doing without constantly watching it.

### Monitoring

- service health
- job health
- transfer throughput
- queue depth
- failed jobs
- disk usage
- cache usage
- RAM pressure
- network failures
- integrity failures

### Notifications

Prefer free/local mechanisms first:

- desktop notifications
- local logs
- webhook support only when explicitly configured

No paid notification dependency.

---

# Phase 11 — CLI

**Goal:** make the Lab controllable from the terminal without requiring a web UI.

Example commands:

```text
td status
td health
td search <query>
td index
td plan <operation>
td jobs
td job <id>
td pause <id>
td resume <id>
td cancel <id>
td verify <path>
td archive <path>
td organize <path>
td backup
```

The CLI must expose plans, authorization boundaries, dry-runs, job state, verification, and audit information.

---

# Phase 12 — Smart Storage & Cache Intelligence

**Goal:** make local cache behavior predictable and resource-aware.

### Intelligence

- hot/cold classification
- access frequency
- cache pressure
- prefetch suggestions
- cache eviction planning
- resource-aware transfers
- RAM-aware concurrency

No automatic eviction of production data.

---

# Phase 13 — Read-only Interoperability

**Goal:** expose safe metadata interfaces without changing TelDrive.

Possible interfaces:

- read-only JSON API
- local IPC
- filesystem metadata views
- export/import of catalog metadata

No write access to TelDrive's database.

---

# Phase 14 — Media Ecosystem

**Goal:** build optional media-aware workflows around the archive.

Potential integrations:

- Jellyfin
- Plex-compatible metadata
- subtitle indexing
- media metadata extraction
- thumbnails
- media library views

Integrations remain sidecar-owned and must not rewrite production storage unexpectedly.

---

# Phase 15 — Media & Document Intelligence

**Goal:** make stored content more understandable without requiring paid AI services.

Possible local tools:

- OCR
- PDF metadata
- document classification
- local speech-to-text
- local embeddings
- local vision models where hardware permits

AI remains advisory.

---

# Phase 16 — Advanced Search

**Goal:** move from filename search toward semantic and content-aware discovery.

Possible layers:

```text
filename/path
   ↓
metadata
   ↓
full text
   ↓
OCR/transcript
   ↓
embeddings
   ↓
semantic search
```

Local-first and free-only by default.

---

# Phase 17 — Optional Local AI

**Goal:** add AI assistance without making AI authoritative.

Possible capabilities:

- natural-language search
- archive suggestions
- organization suggestions
- duplicate explanation
- anomaly explanation
- media classification
- metadata enrichment

AI must never bypass:

```text
Policy
Authorization
Verification
Audit
```

---

# Phase 18 — Storage Intelligence

**Goal:** understand storage economics and behavior without requiring paid services.

Potential features:

- growth forecasting
- storage heatmaps
- category analysis
- duplicate reclaim estimates
- archive recommendations
- transfer cost estimation

Recommendations are advisory unless explicitly authorized.

---

# Phase 19 — Time Machine / Snapshot System

**Goal:** provide durable point-in-time recovery workflows.

Possible implementation:

- snapshot manifests
- incremental snapshots
- retention policies
- snapshot verification
- restore planning
- restore dry-runs
- explicit restore authorization

Restore must be treated as a high-risk operation.

---

# Phase 20 — Cross-Project Integrations

**Goal:** allow other engineering projects to consume Lab capabilities safely.

Potential integrations:

- VAJRA
- Alok Engineering Lab
- local development environments
- dataset workflows
- experiment archives

Integrations use explicit contracts rather than direct production access.

---

# Phase 21 — Advanced / Experimental

Potential experiments:

- content-addressable storage
- local deduplication optimization
- intelligent tiering
- advanced snapshot compression
- distributed workers
- remote worker nodes
- advanced local AI orchestration

Experimental features remain isolated until proven.

---

# Phase 22 — Optional Storage Control Center

**Goal:** provide an optional local UI over the already-proven control plane.

Possible features:

- dashboard
- jobs
- transfers
- archive plans
- search
- storage analytics
- health
- audit history
- configuration visibility

The UI is a client of the control plane, not the authority.

---

# Global Implementation Gates

Every phase should pass these gates where applicable:

```text
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
```

Never skip safety testing because a feature is "only local."

---

# Dependency Order

```text
Phase 0
  ↓
Phase 1
  ↓
Phase 2
  ↓
Phase 3
  ↓
Phase 4
  ↓
Phase 5
  ↓
Phase 6
  ↓
Phase 7
  ↓
Phase 8
  ↓
Phase 9
  ↓
Phase 10
  ↓
Phase 11
  ↓
Phase 12+
```

Some later phases can be developed in parallel after their dependencies are stable, but the safety and durability layers should not be bypassed.

---

# Canonical Product Principle

TelDrive Lab is not a replacement for TelDrive.

It is the **safe engineering control plane around TelDrive**.

The core principle is:

> **Storage remains authoritative. The Lab makes storage observable, verifiable, automatable, searchable, and intelligent without silently taking ownership of it.**
