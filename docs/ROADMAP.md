# you asked

ok so what is our final full detailed roadmap

---

# chatgpt response

Yes. Taking **everything we have discussed so far**—the four-model research synthesis, upstream audit, your existing TelDrive/rclone setup, the new 31-item list, the ₹0 constraint, and the “do not touch existing storage” rule—I would lock the roadmap at this level.

# TelDrive Lab — Final Roadmap

## 0. Non-negotiable architecture rules

These are not phases; they govern **every phase**.

### Protected foundation

We do **not** modify or migrate:

- existing Telegram data
- `~/TelegramRaw`
- `~/TelegramDrive`
- production TelDrive
- `~/teldrive`
- existing PostgreSQL database
- existing rclone services
- existing TelDrive source repository
- DNS/nameservers
- authentication/session state
- `teldrive-original`
- the working Recent `created_at` fix

TelDrive remains the storage/backend authority.

### Lab philosophy

```text
TelDrive
   ↓
existing storage authority

TelDrive Lab
   ↓
control / automation / indexing / observability
```

The Lab is a **sidecar control plane**, not a replacement for TelDrive.

### Safety

Every mutation-capable operation must support:

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

No autonomous destructive behavior.

### Cost

**₹0 / $0.**

Prefer:

- Python/Go/Bash where appropriate
- SQLite
- systemd
- rclone
- existing Docker
- existing TelDrive
- local tools/models
- open-source software

No paid SaaS dependency.

---

# Phase 0 — Lab foundation

**Goal:** establish a clean engineering project without touching production.

Already started:

```text
~/teldrive-lab
```

Current commit:

```text
afdf16a chore: initialize TelDrive Lab
```

Structure:

```text
teldrive-lab/
├── docs/
├── architecture/
├── scripts/
├── automation/
├── search/
├── media/
├── monitoring/
├── integrations/
└── experiments/
```

Next:

- create GitHub repository
- connect local repo
- push baseline
- establish architecture documentation
- establish threat/safety model
- establish testing strategy
- establish production boundary

---

# Phase 1 — Reliability & safety foundation

This is the **most important phase**.

## 1.1 Recent regression protection

Our existing fix must become a permanent invariant:

```text
Recent
 ↓
createdAt
```

not `updatedAt`.

Create regression tests so future work cannot silently break it.

---

## 1.2 Configuration backup

Create safe, versioned templates/backups for:

- TelDrive configuration
- rclone configuration references
- systemd unit definitions
- Docker configuration
- Lab configuration

**Never commit secrets.**

---

## 1.3 Database backup

Build:

```text
backup
 ↓
verify backup exists
 ↓
restore into isolated test location
 ↓
validate
```

The important part is the **restore test**.

A backup that has never been restored is not considered proven.

---

## 1.4 Mount health

Monitor:

```text
TelegramRaw
TelegramDrive
```

including:

- mount availability
- FUSE health
- read/write accessibility
- stale mount detection
- systemd service state

---

## 1.5 Resource monitoring

Because your machine is:

```text
i5-1235U
~8 GB RAM
~475 GB SSD
```

RAM is the major constraint.

Monitor:

- RAM
- CPU
- disk
- disk I/O
- network
- rclone processes
- cache usage
- Docker
- TelDrive
- PostgreSQL

---

## 1.6 Audit/event log

Every Lab operation eventually gets an event:

```text
timestamp
operation
job_id
source
destination
decision
result
checksum
error
```

This becomes critical once automation starts.

---

# Phase 2 — Metadata & Index foundation

Before automation becomes sophisticated, we need to know what exists.

## 2.1 Canonical metadata model

Build a normalized record containing things such as:

```text
path
name
size
MIME
extension
mtime
ctime
hash
source
destination
Telegram identifiers
encryption state
verification state
job state
tags
```

Important distinction:

**This index is not the storage source of truth.**

It is a rebuildable **catalog**.

---

# 2.2 SQLite metadata database

Use SQLite initially because:

- zero cost
- tiny footprint
- local
- reliable
- easy backup
- no additional always-on database

---

# 2.3 Full-text filename/path search

SQLite FTS.

Initial queries:

```bash
td search "VAJRA"
td search "quantum transformer"
td search "*.pdf"
```

---

# 2.4 Saved searches / smart views

Examples:

```text
Large files
Recent files
Unverified
Archives
Datasets
Encrypted
Movies
Backups
Duplicates
Never accessed
```

These are queries, not physical folders.

---

# 2.5 Hash index

Start with:

```text
SHA-256
```

Potentially benchmark BLAKE3 later.

Store:

```text
hash
size
path
source
Telegram identity
verification state
```

This becomes the foundation for deduplication and integrity.

---

# Phase 3 — Durable Job Engine

This is the **big architectural addition from the new list**.

Instead of building independent scripts for everything, we create one durable job system.

```text
                    Job Engine
                        │
       ┌────────────────┼─────────────────┐
       ↓                ↓                 ↓
     Upload           Verify            Backup
       ↓                ↓                 ↓
    Archive          Organize          Snapshot
```

Every job has:

```text
job_id
type
priority
state
created_at
updated_at
attempts
progress
source
destination
checksum
error
retry_at
```

States:

```text
QUEUED
RUNNING
PAUSED
VERIFYING
COMPLETED
FAILED
CANCELLED
```

---

## 3.1 Crash recovery

If the process dies:

```text
RUNNING
   ↓ crash
UNKNOWN
   ↓ restart
RECOVER
   ↓
resume/retry
```

---

## 3.2 Retry engine

Use:

- bounded retries
- exponential backoff
- jitter
- failure classification

Examples:

```text
network timeout → retry

rate limit → delayed retry

invalid path → don't retry blindly

checksum mismatch → verification failure

permission error → pause
```

---

## 3.3 Durable local queue

If Telegram/TelDrive/network disappears:

```text
local request
     ↓
persistent queue
     ↓
wait
     ↓
resume later
```

This gives us the **offline-first** behavior from the new proposal.

---

# Phase 4 — Transfer Manager

Now actual transfer automation.

## 4.1 Upload queue

```text
QUEUED
 ↓
UPLOADING
 ↓
VERIFYING
 ↓
COMPLETED
```

Priorities:

```text
HIGH
NORMAL
LOW
```

---

## 4.2 Controlled upload

Support:

```bash
td upload file.iso
```

but internally:

```text
discover
→ policy
→ hash
→ duplicate check
→ queue
→ transfer
→ verify
→ index
```

---

## 4.3 Download queue

Same architecture:

```text
QUEUED
 ↓
DOWNLOADING
 ↓
VERIFYING
 ↓
COMPLETED
```

---

## 4.4 Automatic recovery

Handle:

- Wi-Fi loss
- Telegram errors
- TelDrive restart
- rclone restart
- Docker restart
- laptop sleep
- stale mount
- rate limits

---

## 4.5 Concurrency controller

We **do not immediately increase concurrency**.

First benchmark.

Then potentially:

```text
small files → modest concurrency
large files → controlled concurrency
degraded network → reduce
healthy network → increase within limits
```

Always bounded.

---

# Phase 5 — Deterministic Organization Engine

This replaces manual:

```text
move → folder → remember
```

with rules.

Example:

```text
*.mkv       → Movies
*.iso       → ISOs
*.parquet   → Datasets
*.pdf       → Research
```

But organization begins with:

```bash
td organize --dry-run
```

Output:

```text
movie.mkv
→ Movies/movie.mkv

paper.pdf
→ Research/paper.pdf
```

Only then:

```bash
td organize --apply
```

---

## 5.1 MIME-aware classification

Don't rely only on extensions.

Use:

- MIME
- extension
- filename
- path
- size
- metadata

---

## 5.2 Policy engine

Rules can eventually express:

```text
projects/** → encrypted
backups/** → encrypted
movies/** → raw
datasets/** → raw
```

This gives us automatic RAW/CRYPT routing.

---

# Phase 6 — Archive Manager

This is one of the most valuable user-facing workflows.

```bash
td archive <file>
```

internally:

```text
file
 ↓
hash
 ↓
duplicate check
 ↓
policy
 ↓
destination selection
 ↓
upload
 ↓
verification
 ↓
metadata record
```

Optional local cleanup is **not part of the default operation**.

---

## 6.1 Archive directory watcher

Eventually:

```text
~/Archive/
```

becomes a staging area.

```text
file appears
 ↓
watcher
 ↓
queue
 ↓
archive workflow
```

---

## 6.2 Local → TelDrive archival

One-way first.

No bidirectional sync yet.

---

# Phase 7 — Duplicate & Integrity System

## 7.1 Duplicate detection

Detect:

```text
movie.mkv
movie (1).mkv
```

with identical hashes.

Report:

```text
2 files
same content
XX GB reclaimable
```

**Never automatically delete.**

---

## 7.2 Integrity verification

At upload:

```text
local hash
 ↓
transfer
 ↓
remote retrieval/check
 ↓
verification
```

where technically practical.

---

## 7.3 Periodic verification

Important archives can be periodically checked.

Potential policies:

```text
critical → monthly
normal → quarterly
cold → on demand
```

---

# Phase 8 — Safety & Lifecycle Management

## 8.1 Trash/quarantine

No immediate destruction.

```text
DELETE REQUEST
 ↓
TRASH
 ↓
retention
 ↓
explicit purge
```

---

## 8.2 Immutable archive

Critical archives can become:

```text
LOCKED
```

Normal operations cannot:

- overwrite
- rename
- delete

until explicitly unlocked.

---

## 8.3 Cleanup engine

Examples:

```text
temporary files > 30d
cache > threshold
verified staging files > retention
```

But:

**protected paths can never be automatically cleaned.**

---

# Phase 9 — Scheduled Backup System

Now backups become first-class jobs.

```text
schedule
 ↓
snapshot
 ↓
checksum
 ↓
archive
 ↓
verify
 ↓
retention
```

Targets can include:

- VAJRA
- Alok Engineering Lab
- Mithila Archives
- configuration
- important documents

---

## 9.1 Retention policies

Example:

```text
daily × 7
weekly × 4
monthly × 6
```

But this will be configurable.

---

## 9.2 Git-aware backups

For source code:

- Git remains authoritative.
- Archive commits/releases/artifacts rather than blindly copying `.git` repeatedly.

---

# Phase 10 — Monitoring & Notifications

Create a unified health model.

```text
TelDrive       ✓
Postgres       ✓
rclone RAW     ✓
rclone CRYPT   ✓
Queue          ✓
Disk           ✓
Network        ✓
Index          ✓
```

---

## 10.1 Event notifications

Examples:

```text
✓ Upload completed
⚠ Upload failed
✓ Backup completed
⚠ Mount unavailable
⚠ Verification failed
```

Notification adapters can eventually include:

- desktop
- Telegram
- webhook

Telegram notification is particularly attractive because it stays within our zero-cost philosophy.

---

# Phase 11 — CLI Control Plane

At this point the CLI becomes the primary interface.

Potential command family:

```text
td status

td upload <file>

td download <file>

td archive <path>

td organize

td verify

td duplicates

td search <query>

td backup

td snapshot

td restore

td queue

td jobs

td cleanup

td monitor

td policy
```

Everything should ultimately call the same underlying engines.

---

# Phase 12 — Smart Storage / Cache Management

Only after telemetry.

We investigate:

```text
hot files
cold files
cache hit rate
cache pressure
disk pressure
read patterns
```

Then potentially implement:

```text
hot → retain
cold → evict
disk pressure → controlled eviction
```

No arbitrary VFS tuning.

---

## Potential future tiering

Conceptually:

```text
             Storage Manager

                 HOT
                  ↓
                SSD
                  ↓
                CACHE
                  ↓
              TelDrive
                  ↓
                COLD
```

But we only implement this if measurements justify it.

---

# Phase 13 — WebDAV & Read-Only Consumers

First external integration:

## WebDAV

Prefer:

```text
READ-ONLY
```

initially.

This lets applications interact with TelDrive without granting them unrestricted write authority.

---

# Phase 14 — Media ecosystem

## Jellyfin

Start:

```text
TelDrive
 ↓
rclone mount
 ↓
Jellyfin
```

Prefer:

- Direct Play
- read-only access
- minimal metadata extraction
- no unnecessary full-file downloads

Then test Intel:

- VA-API
- QSV

if transcoding actually becomes necessary.

---

## Other potential media integrations

Later:

- Navidrome
- Immich
- Kavita/Calibre-Web
- Paperless
- photo/document tools

Each gets evaluated individually rather than installing an ecosystem for the sake of it.

---

# Phase 15 — Media intelligence

Batch-oriented, not always-on.

Possible tools:

```text
FFmpeg
ExifTool
Tesseract/OCR
Whisper
document parsers
```

Generate disposable metadata:

```text
duration
resolution
codec
EXIF
transcript
OCR
thumbnails
```

The original media remains untouched.

---

# Phase 16 — Advanced Search

Search evolves:

### Level 1

```text
filename/path
```

### Level 2

```text
metadata
```

### Level 3

```text
OCR/document text
```

### Level 4

```text
transcripts
```

### Level 5

```text
semantic search
```

---

# Phase 17 — Local AI Layer

**Only now.**

AI is optional.

It never becomes the authority over storage.

Potential functions:

```text
classify
tag
summarize
extract metadata
semantic search
natural-language queries
```

Architecture:

```text
User
 ↓
AI
 ↓
Query/Planning layer
 ↓
Deterministic Storage API
 ↓
Index / Job Engine
```

Not:

```text
User
 ↓
LLM
 ↓
rm -rf
```

---

# Phase 18 — Storage Intelligence

Now we can generate useful reports:

```text
47 duplicates
82 GB reclaimable

126 GB local files
not accessed in 90 days

38 local files
no verified remote copy

17 failed archive jobs

12 GB cache
unused for 30 days
```

This is where the system starts behaving like a real personal storage control plane.

---

# Phase 19 — Snapshots & Time Machine

For supported datasets:

```text
snapshot/
├── 2026-09-10
├── 2026-09-11
└── 2026-09-12
```

Features:

- snapshot creation
- metadata manifest
- integrity verification
- retention
- restore

For source repositories, continue using Git where appropriate.

---

# Phase 20 — Advanced integrations

Potentially:

```text
VAJRA
Alok Engineering Lab
Mithila Heritage Archives
```

All through controlled APIs/jobs.

For example:

```text
VAJRA Engineering Run
        ↓
artifact
        ↓
Storage Manager
        ↓
checksum
        ↓
queue
        ↓
TelDrive
        ↓
verification
        ↓
immutable archive
```

This is a particularly strong use case.

---

# Phase 21 — Advanced / experimental features

Only after the core is mature:

### Multi-account / multi-channel

```text
storage A
storage B
storage C
```

with explicit routing.

### One-way synchronization

```text
TelDrive
   ↓
OfflineArchive
```

### Selective sync

Only selected directories/files.

### Bandwidth scheduler

```text
daytime → low
night → high
```

### Dynamic transfer tuning

Only based on measurements.

### Virtual storage views

Different logical views over the same underlying storage.

### Hybrid/union storage

Only if a real need appears.

---

# Phase 22 — Optional "Storage Control Center"

Finally:

```text
                 TELDRIVE CONTROL CENTER

Storage
────────────────────────
RAW
CRYPT
CACHE
LOCAL

Transfers
────────────────────────
Queued
Uploading
Downloading
Failed
Verified

Health
────────────────────────
TelDrive       ✓
Postgres       ✓
rclone         ✓
Disk           ✓

Intelligence
────────────────────────
Duplicates
Archive candidates
Unverified
Stale files
```

The dashboard is just a client.

The real system remains:

```text
API
 ↓
Job Engine
 ↓
Policy Engine
 ↓
Index
 ↓
rclone/TelDrive
```

---

# What we are explicitly NOT building

This deserves its own permanent document.

### ❌ Storage replacement

We are not replacing TelDrive.

### ❌ Data migration

No re-uploading existing storage just to reorganize it.

### ❌ Database replacement

No unnecessary DB migration.

### ❌ Telegram API abuse

No aggressive polling, mass operations, or concurrency experiments without evidence.

### ❌ Public cloud replacement fantasy

Telegram isn't treated as an unlimited enterprise storage backend.

### ❌ Destructive AI

No AI-driven:

```text
delete
move
overwrite
purge
```

without deterministic policy + explicit authorization.

### ❌ Two-way sync initially

Too much conflict complexity.

### ❌ Unbounded cache

Especially dangerous on an ~8 GB RAM machine.

### ❌ Always-on heavy AI

Batch/local AI only when justified.

### ❌ Telegram-only disaster recovery

Critical data needs an independent recovery strategy.

---

# Final architecture

So the complete system eventually looks like this:

```text
                         USER
                           │
                    ┌──────▼──────┐
                    │ CLI / Web UI│
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Control API│
                    └──────┬──────┘
                           │
             ┌─────────────▼─────────────┐
             │       POLICY ENGINE       │
             │ authorization / dry-run   │
             └─────────────┬─────────────┘
                           │
             ┌─────────────▼─────────────┐
             │        JOB ENGINE         │
             │ queue / retry / recovery  │
             └──────┬─────────┬──────────┘
                    │         │
          ┌─────────▼───┐ ┌───▼─────────┐
          │   INDEX     │ │   AUDIT     │
          │ metadata    │ │ event log   │
          │ FTS / hash  │ │             │
          └─────────────┘ └─────────────┘
                    │
             ┌──────▼──────┐
             │  TRANSFER   │
             │   MANAGER   │
             └──────┬──────┘
                    │
                 rclone
                    │
          ┌─────────▼──────────┐
          │      TelDrive      │
          └─────────┬──────────┘
                    │
                Telegram
```

And around it:

```text
Monitoring
Notifications
Backups
Media tools
OCR
AI
VAJRA
Engineering Lab
Mithila Archives
```

all connect **around** the core rather than modifying the storage authority.

---

# The actual implementation order

Despite the roadmap having 22 phases, **we should not work through them as 22 independent projects**.

Our practical execution sequence is:

```text
NOW
 │
 ▼
0. GitHub + architecture docs
 │
 ▼
1. Reliability / safety
 │
 ▼
2. Metadata + index
 │
 ▼
3. Durable Job Engine
 │
 ▼
4. Transfer Manager
 │
 ▼
5. Organizer
 │
 ▼
6. Archive workflow
 │
 ▼
7. Hash / integrity / duplicates
 │
 ▼
8. Lifecycle / safety
 │
 ▼
9. Backups
 │
 ▼
10. Monitoring
 │
 ▼
11. CLI
 │
 ▼
12. Cache intelligence
 │
 ▼
13. WebDAV / Jellyfin
 │
 ▼
14–16. Media + advanced search
 │
 ▼
17. Local AI
 │
 ▼
18. Storage intelligence
 │
 ▼
19–22. Snapshots / integrations / dashboard / experiments
```

### And one critical rule:

**We don't start Phase 3 until Phase 1 and Phase 2 are proven.**

The whole point is to avoid building an impressive automation layer on top of an unreliable foundation.

So our immediate next milestone after creating the GitHub repo is **not coding the uploader**.

It is to write and commit the **TelDrive Lab Architecture v1 + Safety Contract + Roadmap + Data Model + Job Model**, then review that once before implementation begins.

That gives us a proper engineering specification rather than continuously adding features to a moving target.