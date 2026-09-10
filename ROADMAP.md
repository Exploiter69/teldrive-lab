# TelDrive Lab — Final Canonical Roadmap

**Status:** Canonical implementation roadmap  
**Version:** 2.0 — reconciled 2026-09-11  
**Scope:** Sidecar automation, control, indexing, reliability, and intelligence for the existing TelDrive deployment  
**Cost target:** ₹0 / $0

> **Canonical-source rule:** This root `ROADMAP.md` is the only authoritative roadmap. The former `docs/ROADMAP.md` was the earlier planning transcript and is removed after reconciliation. Future roadmap changes belong here.

---

## 0. Non-negotiable architecture rules

These govern every phase.

### Protected production foundation

The Lab must not modify, migrate, replace, or reorganize without a separate explicit authorization workflow:

- existing Telegram-backed data
- `~/TelegramRaw`
- `~/TelegramDrive`
- production TelDrive
- `~/teldrive`
- existing PostgreSQL database
- existing rclone services/configuration
- existing TelDrive source repository `~/teldrive-project`
- DNS/nameservers
- authentication/session state
- `teldrive-original`
- the working Recent `created_at` fix

TelDrive remains the storage/backend authority.

### Lab philosophy

```text
Existing TelDrive / Telegram / rclone
            ↓
     authoritative storage
            ↓
       TelDrive Lab
            ↓
 control / automation / indexing
 observability / verification
```

The Lab is a **sidecar control plane**, not a replacement storage system.

### Safety lifecycle

Every mutation-capable workflow follows:

```text
PLAN
 ↓
DRY-RUN
 ↓
EXPLICIT AUTHORIZATION
 ↓
EXECUTE
 ↓
VERIFY
 ↓
AUDIT
```

When source, destination, scope, authorization, safety, or verification is uncertain, fail closed.

### Cost

The architecture remains **₹0 / $0**. Prefer local/open-source components, existing infrastructure, SQLite, systemd, rclone, Docker, and local models/tools. No paid SaaS or paid API is a required dependency.

### Resource discipline

The target host has roughly 8 GB RAM and a 12th-gen i5 CPU. Continuous workloads must therefore be lightweight; heavy indexing, hashing, OCR, transcription, media analysis, and AI are bounded, scheduled, or on-demand.

---

# Phase 0 — Lab Foundation

**Goal:** establish a clean, independently rebuildable engineering project without touching production.

### Deliverables

- GitHub repository and local checkout
- canonical architecture
- safety contract
- production boundary
- data model
- durable job model
- architecture decisions
- testing strategy
- runtime/state directory policy
- secret-handling policy

### Current state

The Lab repository exists at `~/teldrive-lab` and is connected to GitHub. Architecture documentation is established. Production remains outside the Lab's ownership boundary.

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
- cache usage
- Docker
- TelDrive
- PostgreSQL

## 1.6 Local audit/event log

Establish the Lab audit foundation for operations and state transitions, including:

```text
timestamp
operation
job_id
source
destination
decision
result
checksum/error when applicable
```

### Phase 1 exit gate

- backup and isolated restore proven
- mount/service health observable
- resource pressure visible
- audit trail exists
- Recent regression protected
- no reliability feature modifies production silently

**Hard dependency:** Phase 1 must pass before Phase 3 Job Engine implementation.

---

# Phase 2 — Metadata & Index Foundation

**Goal:** build a rebuildable catalog of what exists without making the catalog authoritative.

## 2.1 Canonical metadata

Support fields including:

```text
id
path
name
parent_path
size
MIME
extension
created_at
modified_at
sha256
hash_state
source_type
source_identifier
destination_type
destination_identifier
Telegram identifiers
encryption_class
verification_state
tags
job_id
first_seen_at
last_seen_at
```

Unknown values remain unknown/null; never fabricate metadata.

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

Normal successful flow:

```text
QUEUED → RUNNING → VERIFYING → COMPLETED
```

## 3.1 Crash recovery

Persist all state. On restart, recover expired leases, incomplete verification, abandoned transfers, and stale jobs without falsely marking work complete.

## 3.2 Retry engine

Classify failures as transient, rate-limited, permanent, or integrity-related. Use bounded exponential backoff with jitter. Never blindly retry permanent or unsafe failures.

## 3.3 Worker leases

Workers must lease jobs so abandoned work can be recovered without uncontrolled duplicate execution.

## 3.4 Idempotency

Repeated execution must reconcile with current state and avoid accidental duplicate mutation.

## 3.5 Parent/child jobs

Composite workflows may create children such as:

```text
ARCHIVE
 ├─ HASH
 ├─ DUPLICATE_CHECK
 ├─ UPLOAD
 ├─ VERIFY
 └─ INDEX
```

## 3.6 Offline-first behavior

When network/TelDrive is unavailable, durable local work remains queued and resumes only when safe.

### Completion invariant

A job is `COMPLETED` only after required postconditions and verification pass.

### Phase 3 exit gate

Process restart, network interruption, sleep, worker failure, and cancellation must not lose job state, create false completion, or trigger uncontrolled duplicate execution.

---

# Phase 4 — Transfer Manager

**Goal:** provide one controlled transfer layer over local files and the existing TelDrive/rclone interfaces.

### Work

- upload queue
- download queue
- bounded concurrency
- progress reporting
- rate-limit awareness
- retry classification
- exponential backoff
- resumable/recoverable transfers where supported
- checksum-aware verification
- network interruption recovery
- sleep/restart recovery
- TelDrive/rclone failure handling
- transfer benchmarking before tuning concurrency

Example interfaces:

```text
td upload <file>
td download <path>
td verify <path>
```

### Concurrency rule

Do not increase concurrency based on guesswork. Benchmark first, then use bounded resource-aware limits.

### Storage rule

Do not introduce a second storage backend merely to make transfers easier.

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

Potential targets include:

- VAJRA
- Alok Engineering Lab
- Mithila Heritage Archives
- important Lab configuration/documentation

These are future targets, not dependencies of the core Lab.

### Retention

Support configurable daily/weekly/monthly policies.

### Git-aware backups

Git remains authoritative for repositories. The Lab orchestrates useful backups/artifacts rather than replacing Git.

### Restore principle

Restore must be a first-class workflow with verification, not merely the inverse of backup.

---

# Phase 10 — Monitoring & Notifications

**Goal:** provide a unified operational health model.

### Monitor

- TelDrive
- PostgreSQL
- Docker
- rclone RAW mount
- rclone CRYPT mount
- filesystem capacity
- memory/CPU pressure
- network availability
- job queue
- failed jobs
- verification failures
- catalog health
- cache behavior

### Notification adapters

Evaluate zero-cost options first:

- desktop notifications
- Telegram notifications
- local logs
- webhooks where useful

Notifications inform; they never silently authorize risky actions.

---

# Phase 11 — CLI Control Plane

**Goal:** expose the shared engines through one consistent interface.

Planned command family:

```text
td status
td upload
td download
td archive
td organize
td verify
td duplicates
td search
td backup
td snapshot
td restore
td queue
td jobs
td cleanup
td monitor
td policy
```

The CLI is the initial control surface. Future API, PWA, dashboard, or Telegram interfaces must call the same underlying services rather than duplicate business logic.

---

# Phase 12 — Smart Storage & Cache Intelligence

**Goal:** optimize storage behavior using measurement rather than guesses.

### Measure first

- hot/cold usage
- cache hit/miss rate
- disk pressure
- access patterns
- bandwidth utilization
- cache growth

### Then potentially implement

- controlled cache eviction
- selective prefetch
- tiering recommendations
- storage/bandwidth reports

No arbitrary VFS tuning, unlimited read-ahead, or unbounded cache growth.

---

# Phase 13 — Read-only Interoperability

**Goal:** expose existing storage safely to compatible consumers.

Initial candidates:

- WebDAV read-only
- filesystem-compatible consumers
- controlled rclone serving

Write access is deferred until read-only behavior, authentication, isolation, and failure handling are proven.

---

# Phase 14 — Media Ecosystem

**Goal:** make archived media usable without rewriting authoritative originals.

Candidates:

- Jellyfin read-only consumption
- Direct Play first
- Intel QSV / VA-API only if transcoding is actually required
- Navidrome
- Immich
- Kavita / Calibre-Web
- Paperless

Every integration is evaluated independently. No integration receives default authority to reorganize or delete storage.

---

# Phase 15 — Media & Document Intelligence

**Goal:** extract useful metadata without modifying originals.

Potential batch tools:

- FFmpeg
- ExifTool
- Tesseract/OCR
- Whisper/transcription
- document parsers
- thumbnail generation

Potential derived metadata:

- duration
- resolution
- codec
- bitrate
- EXIF
- OCR text
- transcripts
- thumbnails
- document metadata

Heavy workloads are scheduled, bounded, or on-demand.

---

# Phase 16 — Advanced Search

**Goal:** progress from filename search toward content-aware retrieval.

Search levels:

```text
1. filename/path
2. metadata
3. OCR/document text
4. transcripts
5. semantic search
```

Full-text and semantic indexing remain derived state and must not become a storage authority.

---

# Phase 17 — Optional Local AI

**Goal:** add intelligence without giving models storage authority.

Potential uses:

- classification suggestions
- tagging suggestions
- summaries
- natural-language search
- semantic retrieval
- metadata enrichment
- document/media understanding
- archive recommendations

Required boundary:

```text
AI suggestion
     ↓
Deterministic policy/API
     ↓
Authorization
     ↓
Execution
     ↓
Verification
     ↓
Audit
```

AI cannot authorize deletion, migration, configuration changes, database changes, or unrestricted storage mutations.

Local/open-source models are preferred. Remote/free tiers may be evaluated only when compatible with ₹0/$0, privacy, reliability, and rate-limit requirements.

---

# Phase 18 — Storage Intelligence

**Goal:** turn the catalog into actionable storage knowledge.

Reports may include:

- duplicate data
- potentially reclaimable GB
- stale local files
- missing verified remote copies
- failed archival jobs
- failed verification
- cache statistics
- storage growth
- hot/cold data
- orphaned metadata
- backup coverage

The intelligence layer recommends; safety and policy layers decide.

---

# Phase 19 — Time Machine / Snapshot System

**Goal:** provide controlled historical views and reliable restoration.

### Work

- snapshot manifests
- snapshot metadata
- checksum verification
- retention policies
- restore planning
- restore verification
- project-aware snapshots

Git remains authoritative for Git repositories. TelDrive Lab provides storage and backup orchestration rather than replacing Git.

---

# Phase 20 — Cross-Project Integrations

**Goal:** connect the Lab to other engineering systems without coupling their cores.

Planned integrations:

- VAJRA
- Alok Engineering Lab
- Mithila Heritage Archives

Example future flow:

```text
VAJRA Engineering Run
        ↓
Artifact
        ↓
TelDrive Lab Storage Manager
        ↓
Checksum
        ↓
Durable Queue
        ↓
TelDrive
        ↓
Verification
        ↓
Immutable Archive
```

Integrations communicate through stable interfaces and artifacts, not shared internal databases.

---

# Phase 21 — Advanced / Experimental Features

Deferred until the core system is mature.

Candidates:

- multiple Telegram accounts/channels
- selective synchronization
- one-way synchronization
- bandwidth scheduling
- adaptive transfer tuning
- virtual storage views
- advanced watched-directory automation
- storage-policy simulations
- additional compatibility layers
- experimental automation workers

### Explicitly deferred

Two-way synchronization is not introduced until one-way workflows have proven their safety and recovery semantics.

---

# Phase 22 — Optional Storage Control Center

**Goal:** provide a unified human interface after the underlying engines are mature.

Possible UI:

- storage overview
- job queue
- transfers
- verification status
- health
- duplicate reports
- backups
- snapshots
- policies
- search
- media views
- alerts

Conceptual architecture:

```text
                 ┌────────────────────┐
                 │ CLI / Web / PWA    │
                 │ Telegram / API     │
                 └─────────┬──────────┘
                           ↓
                  Shared Control API
                           ↓
       ┌───────────────────┼───────────────────┐
       ↓                   ↓                   ↓
   Policy Engine      Job Engine         Catalog/Search
       ↓                   ↓                   ↓
       └───────────────────┼───────────────────┘
                           ↓
                    Transfer Manager
                           ↓
              Existing TelDrive / rclone
```

The UI is never the authority. Shared services, policy, authorization, verification, and audit remain authoritative.

---

# Global Implementation Gates

A phase is **not complete** because its code exists.

Every phase must satisfy, as applicable:

1. implementation complete
2. unit/integration tests pass
3. failure behavior tested
4. safety invariants tested
5. restart/recovery behavior tested where relevant
6. resource behavior tested on the target host
7. production boundary verified
8. documentation updated
9. no secrets committed
10. Git state clean and changes recorded

### Dependency order

```text
Phase 0
  ↓
Phase 1 + Phase 2
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
Phase 8 + Phase 9
  ↓
Phase 10 + Phase 11
  ↓
Phase 12 + Phase 13
  ↓
Phase 14–16
  ↓
Phase 17
  ↓
Phase 18–22
```

Later phases may be researched early, but implementation should respect dependency and safety gates.

---

# Canonical Product Principle

> **TelDrive Lab makes the existing TelDrive storage system reliable, observable, searchable, automatable, verifiable, and safely extensible — without requiring migration, replacement, or loss of human control.**

The Lab's most important property is not maximum automation. It is **durable, reversible, verified automation with the existing storage preserved as the authority.**
