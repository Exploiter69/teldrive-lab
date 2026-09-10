# TelDrive Lab — Roadmap

**Status:** Canonical implementation roadmap  
**Version:** 1.0  
**Scope:** Sidecar automation, control, indexing, reliability, and intelligence for an existing TelDrive deployment  
**Cost target:** ₹0 / $0

---

## 1. Mission

TelDrive Lab is a **sidecar control plane and power-user ecosystem** around the existing TelDrive deployment.

It is not a replacement for TelDrive, Telegram, rclone, PostgreSQL, or the existing storage layout. The Lab adds durable jobs, deterministic automation, metadata indexing, verification, monitoring, search, controlled workflows, and optional intelligence while keeping the existing storage system authoritative.

The central objective is:

> Make the existing TelDrive storage reliable, observable, searchable, automatable, and safely extensible without migrating or rebuilding the existing system.

---

## 2. Non-Negotiable Rules

These rules apply to every phase.

1. **TelDrive remains the storage/backend authority.**
2. **Existing Telegram-backed data is protected.**
3. **No migration, re-upload, replacement, or storage reorganization as a prerequisite for the Lab.**
4. **The Lab is independently removable and rebuildable.**
5. **The Lab catalog is rebuildable and never becomes the source of truth for stored data.**
6. **Destructive operations are never automatic by default.**
7. **Mutating workflows follow:**
   `PLAN → DRY-RUN → EXPLICIT AUTHORIZATION → EXECUTE → VERIFY → AUDIT`
8. **Transfer success is not the same as archival completion; required verification must pass.**
9. **Duplicate detection is informational unless the user explicitly authorizes a destructive action.**
10. **AI is advisory and cannot authorize deletion, migration, configuration changes, database changes, or storage mutations.**
11. **Telegram API usage remains conservative and rate-aware.**
12. **No secrets, credentials, tokens, session material, or private production state are committed to Git.**
13. **The system must remain useful without AI.**
14. **Heavy workloads are bounded, scheduled, and resource-aware for the target ~8 GB RAM laptop.**
15. **Every important state-changing action must be auditable.**
16. **When safety, authorization, source, destination, or verification is uncertain, fail closed.**

---

## 3. Implementation Strategy

The project is deliberately staged so that higher-level automation cannot outrun the reliability and safety foundations beneath it.

```text
Foundation
   ↓
Reliability & Safety
   ↓
Metadata & Index
   ↓
Durable Job Engine
   ↓
Transfer Manager
   ↓
Deterministic Organization
   ↓
Archive Workflows
   ↓
Integrity & Duplicate Intelligence
   ↓
Lifecycle / Backup / Recovery
   ↓
Monitoring / Notifications / CLI
   ↓
Cache & Storage Intelligence
   ↓
Read-only Interoperability / Media
   ↓
Advanced Search / OCR / Transcription
   ↓
Optional Local AI
   ↓
Cross-project Integrations / Dashboard / Experiments
```

**Dependency rule:** do not begin a later phase merely because its feature is attractive. Complete and validate the foundations required by that phase first.

---

# Phase 0 — Lab Foundation

**Goal:** Establish the project as a safe, documented sidecar before touching implementation.

### Deliverables

- GitHub repository and local checkout
- architecture baseline
- safety contract
- production boundary
- data model
- durable job model
- architecture decision record
- testing strategy
- runtime/state directory policy
- secret-handling policy

### Current state

The Lab repository is initialized and connected to GitHub. Existing TelDrive production remains outside the Lab's ownership boundary.

### Exit criteria

- architecture documents are internally consistent
- protected production boundary is explicit
- no implementation assumes ownership of existing storage
- safety invariants are testable

---

# Phase 1 — Reliability & Safety

**Goal:** Build confidence before adding automation.

### Work

1. Protect the existing Recent-files regression with a repeatable compatibility/regression check.
2. Establish safe configuration backup procedures.
3. Back up the production database using supported mechanisms.
4. Perform an **isolated actual restore test**; a backup that has never been restored is not considered proven.
5. Monitor rclone RAW and CRYPT mount health.
6. Monitor TelDrive, PostgreSQL, Docker, filesystem capacity, memory, CPU, and network health.
7. Introduce a local Lab audit/event log.
8. Detect stale FUSE mounts, failed services, incomplete operations, and resource pressure without automatically performing risky remediation.

### Exit criteria

- backup and restore procedure proven
- mount/service health observable
- resource pressure visible
- audit trail exists
- no reliability feature modifies production data silently

**Dependency:** Phase 1 must be proven before Phase 3 Job Engine work begins.

---

# Phase 2 — Metadata & Index

**Goal:** Build a rebuildable catalog of what exists without making the catalog authoritative.

### Work

- canonical file metadata model
- local SQLite catalog
- incremental filesystem discovery
- TelDrive/rclone metadata ingestion where safely available
- SHA-256 checksum records
- hash index
- filename/path search
- MIME/extension/size/time indexes
- source/destination/encryption/verification state
- Telegram identifiers where available
- tags and user metadata
- saved searches / smart views
- catalog consistency checks
- full-text search preparation

### Important design rule

The catalog lives under Lab runtime state, for example:

```text
~/.local/share/teldrive-lab/catalog.db
```

It is **rebuildable derived state**. Loss of the catalog must not mean loss of storage data.

### Exit criteria

- catalog can be rebuilt from authoritative sources
- search works on indexed metadata
- indexing is incremental and bounded
- hashes are deterministic
- catalog corruption does not corrupt production storage

---

# Phase 3 — Durable Job Engine

**Goal:** Replace fragile one-off automation with a durable execution model.

### Core job types

- UPLOAD
- DOWNLOAD
- ARCHIVE
- VERIFY
- BACKUP
- SNAPSHOT
- ORGANIZE
- CLEANUP
- INDEX
- RESTORE

### Required capabilities

- durable persistence
- explicit state machine
- priorities
- progress tracking
- cancellation
- retry scheduling
- transient/rate-limit/permanent/integrity failure classification
- bounded exponential backoff with jitter
- worker leases
- abandoned-job recovery
- idempotency
- parent/child jobs
- crash recovery
- offline-first queue behavior
- audited state transitions

### Completion invariant

A job is not `COMPLETED` merely because a command returned success. Required postconditions and verification must pass.

### Exit criteria

A process restart, network interruption, sleep cycle, or worker failure must not create false completion, lose job state, or cause uncontrolled duplicate execution.

---

# Phase 4 — Transfer Manager

**Goal:** Provide one controlled transfer layer for local files and the existing TelDrive/rclone interfaces.

### Work

- upload queue
- download queue
- bounded concurrency
- progress reporting
- rate-limit awareness
- retry classification
- backoff
- resumable/recoverable transfers where supported
- checksum-aware verification
- network interruption recovery
- sleep/restart recovery
- TelDrive/rclone failure handling
- transfer benchmarking before concurrency tuning

### Initial interface examples

```text
td upload <file>
td download <path>
td verify <path>
td jobs
```

### Rule

Do not introduce a second storage backend merely to make transfers easier.

---

# Phase 5 — Deterministic Organization

**Goal:** Make organization predictable and policy-driven.

### Classification inputs

- extension
- MIME type
- filename
- path
- size
- timestamps
- existing metadata
- explicit user rules

### Work

- rule engine
- RAW vs CRYPT routing policy
- destination policies
- dry-run planner
- explicit apply operation
- conflict handling
- audit records

### Example

```text
td organize --dry-run
```

Only after reviewing the plan may an explicitly authorized apply operation mutate files.

**AI is not the organization authority.** AI may propose a classification later, but deterministic policy decides whether and how it is applied.

---

# Phase 6 — Archive Manager

**Goal:** Turn archival into a safe, composable workflow.

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

### Composite command

```text
td archive <file>
```

The workflow may eventually support watched directories such as an archive inbox, but local deletion is **not** part of the default archive operation.

### Initial direction

Start with **one-way local → TelDrive archival**. Two-way synchronization is explicitly deferred.

---

# Phase 7 — Integrity & Duplicate Intelligence

**Goal:** Know whether stored copies are trustworthy and identify duplicate data without destructive automation.

### Work

- SHA-256 checksum database
- duplicate groups by checksum + size
- upload verification
- download verification
- periodic verification
- stale checksum detection
- integrity reports
- missing verified-copy reports
- optional benchmark of BLAKE3 before considering it

### Safety rule

```text
DUPLICATE FOUND ≠ DELETE
```

The system may report reclaimable space, but deletion requires a separate explicit authorization workflow.

---

# Phase 8 — Safety & Lifecycle Management

**Goal:** Make cleanup possible without making accidental destruction easy.

### Work

- quarantine/trash area
- safety window before purge
- retention policies
- explicit purge
- immutable/locked archive mode
- cleanup planner
- protected-path enforcement
- cleanup verification
- audit trail for lifecycle operations

### Default behavior

Cleanup is conservative. Protected paths and uncertain states cause the operation to stop rather than guess.

---

# Phase 9 — Scheduled Backups & Snapshots

**Goal:** Automate proven backup workflows using the durable Job Engine.

### Work

- scheduled backups
- snapshots
- manifests
- checksums
- verification
- retention
- restore workflows
- Git-aware project backups
- daily/weekly/monthly policy options

### Initial backup targets

- VAJRA
- Alok Engineering Lab
- Mithila Heritage Archives
- important Lab configuration/documentation

These are **future targets**, not dependencies of the TelDrive Lab core.

### Principle

A backup is considered useful only when its integrity and restore path are understood.

---

# Phase 10 — Monitoring & Notifications

**Goal:** Provide a unified operational view.

### Monitor

- TelDrive
- PostgreSQL
- Docker
- rclone RAW mount
- rclone CRYPT mount
- filesystem capacity
- memory pressure
- CPU pressure
- network availability
- job queue
- failed jobs
- verification failures
- catalog health
- cache behavior

### Notifications

Evaluate zero-cost channels first:

- desktop notifications
- Telegram notifications
- local logs
- webhooks where useful

Notifications inform; they do not silently authorize risky actions.

---

# Phase 11 — CLI Control Plane

**Goal:** Make the system usable through one consistent interface.

### Planned commands

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

All commands should call shared services rather than implementing independent business logic.

Future interfaces may include an API, dashboard, PWA, or Telegram bot, but the CLI is the initial control surface.

---

# Phase 12 — Smart Storage & Cache Intelligence

**Goal:** Optimize storage behavior using measurement rather than guesses.

### Work

- hot/cold usage telemetry
- cache hit/miss measurement
- disk-pressure telemetry
- access-pattern analysis
- controlled cache eviction
- selective prefetch where justified
- tiering recommendations
- bandwidth/storage utilization reports

### Rule

No arbitrary VFS tuning, unlimited read-ahead, or unbounded cache growth.

Measure first; change second.

---

# Phase 13 — Read-only Interoperability

**Goal:** Expose existing storage safely to compatible consumers.

### First candidates

- WebDAV read-only
- filesystem-compatible consumers
- controlled rclone serving

Write access is deliberately deferred until read-only behavior, authentication, isolation, and failure handling are proven.

---

# Phase 14 — Media Ecosystem

**Goal:** Turn archived media into usable personal infrastructure without rewriting originals.

### Candidates

- Jellyfin read-only consumption
- Direct Play first
- Intel QSV / VA-API if transcoding is actually required
- Navidrome
- Immich
- Kavita / Calibre-Web
- Paperless

Each integration is evaluated independently. No integration gets permission to reorganize or delete the authoritative storage by default.

---

# Phase 15 — Media & Document Intelligence

**Goal:** Extract useful metadata without modifying originals.

### Batch/disposable tooling

- FFmpeg
- ExifTool
- Tesseract/OCR
- Whisper/transcription
- document parsers
- thumbnail generation

### Possible metadata

- duration
- resolution
- codec
- bitrate
- EXIF
- OCR text
- transcripts
- thumbnails
- document metadata

Heavy processing should be scheduled or on-demand on the resource-constrained host.

---

# Phase 16 — Advanced Search

**Goal:** Progress from filename search toward content-aware retrieval.

### Search levels

1. filename/path
2. metadata
3. OCR/document text
4. transcripts
5. semantic search

Full-text indexing should be added only after the metadata foundation is stable.

---

# Phase 17 — Optional Local AI

**Goal:** Add intelligence without giving models authority over storage.

### Possible uses

- automatic classification suggestions
- tagging suggestions
- summaries
- natural-language search
- semantic retrieval
- metadata enrichment
- document/media understanding
- archive recommendations

### Architecture rule

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

AI never receives unrestricted mutation authority.

Local/open-source models are preferred. Remote/free tiers may be evaluated only when they remain compatible with the ₹0/$0 constraint and do not introduce unacceptable privacy or reliability dependencies.

---

# Phase 18 — Storage Intelligence

**Goal:** Turn the catalog into actionable storage knowledge.

### Reports

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

**Goal:** Provide controlled historical views and reliable restoration.

### Work

- snapshot manifests
- snapshot metadata
- checksum verification
- retention policies
- restore planning
- restore verification
- project-aware snapshots

Git remains the authority for Git repositories. TelDrive Lab provides storage/backup orchestration rather than replacing Git.

---

# Phase 20 — Cross-Project Integrations

**Goal:** Connect the Lab to other personal engineering systems without coupling their cores.

### Planned integrations

- VAJRA
- Alok Engineering Lab
- Mithila Heritage Archives

Example future VAJRA flow:

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

Integrations communicate through stable interfaces and artifacts rather than sharing internal databases.

---

# Phase 21 — Advanced / Experimental Features

These are intentionally deferred until the core system is mature.

### Candidates

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

Two-way synchronization should not be introduced until one-way workflows have proven their safety and recovery semantics.

---

# Phase 22 — Optional Storage Control Center

**Goal:** Provide a unified human interface once the underlying system is mature.

### Possible UI

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

Architecture:

```text
                 ┌─────────────────┐
                 │ CLI / Web / PWA │
                 │ Telegram / API  │
                 └────────┬────────┘
                          ↓
                 ┌─────────────────┐
                 │   Control Plane │
                 └────────┬────────┘
                          ↓
        ┌─────────────────┼─────────────────┐
        ↓                 ↓                 ↓
  Policy Engine      Job Engine        Metadata Index
        ↓                 ↓                 ↓
        └──────────┬──────┴──────┬──────────┘
                   ↓             ↓
             Transfer Manager   Audit
                   ↓
          Existing TelDrive/rclone
                   ↓
             Telegram storage
```

The UI is a client. It is not the architecture itself.

---

# 4. Feature Mapping from the Power-user List

The broader feature inventory is intentionally mapped into the staged architecture rather than implemented as disconnected scripts.

| Feature | Roadmap phase |
|---|---|
| Watched-directory upload/download | 4 / 6 / 21 |
| Deterministic organization | 5 |
| Local → Telegram archive | 6 |
| Telegram → local sync | 21, one-way first |
| Scheduled backups | 9 |
| SHA-256 duplicate detection | 7 |
| RAW vs CRYPT policy | 5 |
| Snapshots/versioning | 9 / 19 |
| MIME/media categorization | 2 / 5 / 15 |
| Search/indexing | 2 / 16 |
| Integrity verification | 1 / 7 |
| Dynamic transfer concurrency | 4 / 21 |
| Cache management | 12 |
| Dashboard | 22 |
| Notifications | 10 |
| Cleanup/retention | 8 |
| Quotas | 5 / 8 / 12 |
| Multiple accounts/channels | 21 |
| Upload queue/priorities | 3 / 4 |
| Bandwidth scheduler | 21 |
| Composite `archive` command | 6 / 11 |
| Trash/safety window | 8 |
| Immutable archive | 8 / 19 |
| Automatic checksum DB | 2 / 7 |
| Offline-first behavior | 3 / 4 |
| Storage intelligence | 18 |
| VAJRA integration | 20 |
| Alok Engineering Lab integration | 20 |
| Mithila Archives integration | 20 |

---

# 5. What Is Explicitly Rejected

The following are outside the default architecture unless a future decision explicitly changes the policy:

- replacing TelDrive
- replacing PostgreSQL
- replacing Telegram-backed storage
- migrating existing files to a new storage system
- re-uploading existing data as a prerequisite
- destructive automatic deduplication
- arbitrary production reorganization
- unauthenticated public storage exposure
- uncontrolled Telegram API traffic
- treating AI output as authorization
- always-on heavy AI on the laptop
- unbounded cache/read-ahead
- two-way sync as an early feature
- automatic database/schema replacement
- arbitrary Docker/container replacement of production
- DNS/nameserver changes by the Lab
- Telegram as the only disaster-recovery mechanism
- introducing a second storage backend merely for convenience

A rejected idea can only return through an explicit architecture decision that documents its safety and operational justification.

---

# 6. Testing Philosophy

Every phase must have a concrete proof, not merely code that exists.

### Required test categories

- unit tests
- integration tests
- failure injection where practical
- dry-run tests
- authorization tests
- idempotency tests
- crash/restart tests
- network interruption tests
- verification tests
- protected-path tests
- resource-limit tests
- compatibility tests against the existing TelDrive deployment
- restore tests for backup features

### Mutation rule

A destructive or production-affecting feature is not considered complete until its safety behavior has been tested independently from its happy path.

---

# 7. Resource Strategy

The target host is a laptop-class system with approximately 8 GB RAM.

Therefore:

- prefer SQLite over heavyweight infrastructure
- prefer systemd over unnecessary always-on orchestration
- bound workers and queues
- avoid redundant daemons
- perform large scans incrementally
- schedule expensive hashing/media/OCR jobs
- avoid loading large datasets into RAM
- measure transfer/cache performance before tuning
- use local AI only when workload and memory budget justify it
- prefer batch/disposable AI workloads over permanent services
- keep the control plane lightweight

CPU availability does not justify ignoring RAM pressure.

---

# 8. Zero-cost Strategy

The architecture targets **₹0 / $0** ongoing infrastructure cost.

Preferred building blocks:

- existing Linux host
- Python / Go / Bash where appropriate
- SQLite
- systemd
- rclone
- existing TelDrive
- Docker where justified
- open-source utilities
- local/open-source AI
- free remote services only when genuinely free and optional

No architectural decision should quietly introduce a paid API, subscription, hosted database, paid storage layer, or pay-as-you-go dependency.

---

# 9. Practical Build Order

The implementation order is intentionally strict:

```text
0  GitHub + architecture contracts
1  Reliability / safety
2  Metadata / index
3  Durable Job Engine
4  Transfer Manager
5  Deterministic Organizer
6  Archive Manager
7  Hash / integrity / duplicates
8  Lifecycle / safety window
9  Backups / snapshots
10 Monitoring / notifications
11 CLI control plane
12 Cache / storage intelligence
13 WebDAV / read-only consumers
14 Media ecosystem
15 Media / document intelligence
16 Advanced search
17 Local AI
18 Storage intelligence
19 Time Machine / snapshots
20 Cross-project integrations
21 Advanced experiments
22 Optional control center
```

### Gate rule

A phase may be marked complete only when:

1. implementation exists,
2. tests exist,
3. failure behavior is understood,
4. safety invariants are preserved,
5. resource behavior is acceptable,
6. documentation reflects the actual implementation.

---

# 10. Definition of Done for TelDrive Lab

TelDrive Lab is successful when it can provide a durable, observable, searchable, verifiable, and automation-friendly control plane around the existing TelDrive deployment while satisfying all of these invariants:

- existing storage remains authoritative
- existing production remains intact
- the Lab can be deleted and rebuilt independently
- metadata can be rebuilt
- jobs survive process crashes and network interruptions
- transfers are bounded and recoverable
- archival completion requires verification
- destructive operations require explicit authorization
- every important mutation is auditable
- AI remains optional and non-authoritative
- the system works without paid infrastructure
- the laptop remains within practical resource limits
- integrations do not create hidden coupling
- Telegram API usage remains conservative

**The roadmap optimizes for reliability first, automation second, intelligence third.**