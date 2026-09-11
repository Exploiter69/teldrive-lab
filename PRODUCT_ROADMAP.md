# TelDrive Lab — Product Roadmap

> Canonical product strategy after the 0–22 engineering audit and independent Gemini, Perplexity, Grok, and Claude research.

## 1. Product identity

**TelDrive Lab is a local-first, auditable storage control plane and intelligent archive layer around TelDrive and other storage providers.**

It makes heterogeneous and imperfect storage usable by adding durable jobs, policy, authorization, verification, metadata, organization, search, recovery, monitoring, and safe automation.

TelDrive remains the production storage authority. Telegram is a supported storage substrate, not a promise of unlimited or permanent storage. The Lab must remain useful if Telegram becomes unavailable or is replaced.

### The product is NOT

- a replacement for TelDrive
- a replacement for rclone
- a filesystem implementation
- a Jellyfin/Plex/Emby competitor
- a Netflix-style OTT platform
- a general-purpose automation platform
- an autonomous AI storage administrator
- a multi-tenant Telegram storage service

### The differentiation test

A user should be able to answer:

> Why use TelDrive Lab instead of Telegram + rclone + Jellyfin?

Because TelDrive Lab provides the missing **trust/control layer**: authoritative local metadata, durable restart-safe workflows, policy and authorization boundaries, verification evidence, integrity and duplicate intelligence, recovery planning, audit history, safe organization, search, provider health, and controlled interoperability.

---

## 2. Non-negotiable product invariants

Every future capability inherits these rules.

```text
AI proposes
  ↓
Policy evaluates
  ↓
Authorization permits
  ↓
Execution mutates
  ↓
Verification proves
  ↓
Audit records
```

- Production TelDrive remains the storage authority.
- No direct TelDrive PostgreSQL writes.
- No silent production delete/rename/move/overwrite/reorganization.
- Duplicate detection never implies deletion.
- AI never self-authorizes.
- Untrusted workers never receive implicit mutation authority.
- Core functionality works without an LLM.
- Optional providers fail explicitly; no paid fallback.
- Derived catalogs and indexes are rebuildable.
- Destructive operations require explicit authorization and verification.
- Sidecar state remains disposable where possible.
- ₹0/$0 is a hard constraint: no paid API, inference, hosting, SaaS, or notification dependency.
- Resource usage must remain realistic for the primary i5-1235U / 8 GB RAM environment.

---

## 3. Strategic architecture

```text
                    USERS / CLIENTS
                          │
        ┌─────────────────┼──────────────────┐
        │                 │                  │
       CLI             HTTP/API        External tools
        │                 │                  │
        └─────────────────┼──────────────────┘
                          ▼
              ┌────────────────────────┐
              │     TELDRIVE LAB       │
              │                        │
              │ Policy / Auth          │
              │ Durable Jobs            │
              │ Transfer Control        │
              │ Metadata / Search       │
              │ Integrity / Recovery    │
              │ Organization            │
              │ Monitoring / Audit      │
              │ Intelligence            │
              └───────────┬────────────┘
                          ▼
                STORAGE ABSTRACTION
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
    TelDrive/         Local FS /         Future
    Telegram           rclone             providers
        │
        └──────────────┬──────────────────┘
                       ▼
             interoperability layer
             rclone / HTTP / WebDAV
                       │
                       ▼
                 Jellyfin etc.
```

### Ownership boundaries

| Component | Owns | Does not own |
|---|---|---|
| TelDrive Lab | policy, jobs, metadata, verification, audit, organization, search, recovery | production storage authority |
| TelDrive / Telegram | stored objects and provider state | Lab policy/audit |
| rclone | transfer/protocol/mount primitives | Lab authorization or product metadata |
| Jellyfin | media presentation, playback, profiles, watch state, transcoding orchestration | storage policy |
| FFmpeg | media processing primitives | storage authority |
| External automation | cross-system orchestration | Lab internal safety semantics |
| AI | suggestions, explanations, natural-language interpretation | authorization, deletion, retention, restore authority |

---

# 4. Product evolution

The old Phase 0–22 sequence remains the **engineering audit history**. It should not be treated as the long-term product roadmap. Future work is organized into product stages.

## Stage 1 — Foundation: DONE

The control-plane foundation is substantially complete and audited.

Includes:

- repository/runtime separation
- deterministic metadata/catalog foundations
- durable jobs
- transfer boundary
- deterministic organization
- archive workflows
- integrity and duplicate reporting
- lifecycle safety
- backups and snapshots
- monitoring and health
- operator CLI/control plane
- storage intelligence
- read-only API/IPC surfaces
- media/document discovery foundations
- local search/intelligence foundations
- safe experimental contracts
- local control-center foundation

**Exit:** Phases 0–22 pass their defined engineering gates. This means capability exists safely in code/tests/contracts; it does not mean every optional provider is installed or that the product is consumer-polished.

## Stage 2 — Productization: NEXT

Turn the proven Lab into something a user can reliably install, understand, operate, and recover.

### MUST

- one documented installation path
- first-run configuration and capability detection
- clear distinction between core and optional providers
- health dashboard with actionable failures
- durable job visibility and retry controls
- consistent CLI/API semantics
- safe configuration validation
- backup/restore drill documentation
- provider availability/degraded-state reporting
- honest Telegram capacity/risk messaging
- complete operator documentation

### SHOULD

- polished local control center
- operation templates
- import/export of Lab metadata and manifests
- simple upgrade/migration procedure
- event/audit timeline

### Definition of done

A new installation can be understood and operated without reading the implementation source, and loss of the Lab catalog does not imply loss of stored data.

## Stage 3 — Provider Resilience & Independence

Make Telegram important but replaceable.

### MUST

- explicit provider abstraction/capability model
- provider-independent file/object manifest
- provider health and capability discovery
- resumable/retry-aware provider operations
- provider error classification and backpressure
- exportable manifests
- provider evacuation/copy planning
- degraded operation when a provider is unavailable
- local authoritative metadata independent of Telegram message history

### SHOULD

- migration workflows between providers
- verified-copy tracking
- local filesystem provider hardened as a first-class baseline
- rclone-compatible provider paths

### COULD

- S3-compatible adapter
- additional object providers where zero-cost operation is realistic

### Rule

**If moving bytes, prefer mature transfer tooling. If deciding, proving, indexing, or recovering, TelDrive Lab owns the semantics.**

## Stage 4 — Interoperability

Make Lab-managed storage useful to existing software instead of rebuilding that software.

### MUST

- stable read-only HTTP/API surface
- safe HTTP range/read access where architecture permits
- rclone integration as a first-class consumer
- authenticated, bounded WebDAV adapter/gateway if justified by implementation review
- filesystem/local-provider interoperability
- capability negotiation and clear consistency semantics

### SHOULD

- Jellyfin integration/setup tooling
- media-aware materialization and cache controls
- webhooks/events for external automation

### COULD

- S3 gateway/adapter
- FUSE experiment

### DO NOT BUILD

- SMB server
- NFS server
- custom POSIX filesystem
- replacement for rclone's transfer engine

WebDAV is strategically important, but it is an adapter/interoperability boundary, not a second storage engine.

## Stage 5 — Media as Data, Not OTT

Use media as a high-value workload while delegating playback to mature software.

### MUST

- reliable media discovery
- technical metadata
- subtitle indexing
- stable library metadata exports
- cache/materialization controls
- health/latency visibility

### SHOULD

- Jellyfin integration guide and setup automation
- media prefetch suggestions
- direct-play-friendly organization guidance
- poster/thumbnail caching where dependency cost is acceptable

### COULD

- lightweight browser preview for simple supported media

### DO NOT BUILD

- full OTT platform
- Netflix-style recommendation engine
- custom transcoding farm
- TV/mobile native clients before proven demand
- second full media server

**Jellyfin owns playback, watch history, profiles, subtitles, clients, and transcoding orchestration. TelDrive Lab owns storage reliability and access semantics.**

## Stage 6 — Safe Automation & Integrations

Automate Lab-owned operations without becoming a generic workflow platform.

### MUST

- scheduled durable jobs
- event-driven ingestion
- verification after mutation
- job dependencies and bounded retries
- pause/resume/degraded behavior
- notifications using local/free mechanisms
- webhook/event emission
- explicit approval points for high-risk operations

### SHOULD

- ingestion templates
- backup/verification schedules
- archive watcher
- integration hooks for Jellyfin and external tools

### External boundary

Cross-system orchestration can be delegated to cron, n8n, GitHub Actions, or similar external tools. TelDrive Lab should expose safe events and APIs rather than absorbing an entire automation ecosystem.

## Stage 7 — Intelligence

Deterministic retrieval remains the foundation; AI improves interpretation rather than authority.

### MUST

- strong lexical/metadata search
- structured filters
- OCR/transcript indexing where local tools are available
- deterministic duplicate/anomaly explanations
- explainable recommendations

### SHOULD

- natural-language search over deterministic retrieval
- archive and organization suggestions
- metadata enrichment suggestions
- transcript/document summaries
- local model adapters

### AI operating level

Target **advisory Level 2–3**. Carefully bounded planning assistance is acceptable; autonomous destructive storage administration is not.

AI must never independently:

- delete data
- overwrite data
- change retention policy
- authorize destructive cleanup
- restore over existing content
- expose private data
- migrate the only verified copy

## Stage 8 — Advanced Experiments

Only after Stages 2–7 are stable.

Potential experiments:

- content-addressable storage optimization
- advanced deduplication research
- intelligent tiering
- compressed snapshot optimization
- distributed workers
- remote worker nodes
- advanced local AI orchestration
- FUSE

Experiments must remain isolated and cannot weaken the core safety model.

---

# 5. Telegram operating model

Telegram is a **supported provider/substrate**, not a hard product guarantee.

The Lab should optimize for the maximum sustainable legitimate engineering envelope rather than trying to exploit undocumented limits.

### Good workloads

- personal archives
- write-once or infrequently changing media
- selected backups with independent verification
- asynchronous ingestion
- cold/warm storage with local caching
- bounded background transfers

### Risky workloads

- millions of tiny files as a normal filesystem
- high-concurrency streaming
- constant random seeking against uncached remote data
- repeated full-library rescans
- sustained maximum-rate uploads/downloads
- single-account sole-copy storage
- public multi-user storage

### Absolute DO NOT BUILD

- account farms
- rate-limit/flood-wait evasion
- proxy rotation to defeat enforcement
- spam or unsolicited distribution
- prohibited-content automation
- claims of unlimited guaranteed storage or throughput

Do not hardcode undocumented Telegram thresholds. Where a limit is relevant, record whether it is an official published limit, observed behavior, or an engineering estimate.

### Required resilience

When Telegram degrades or disappears:

1. pause affected jobs
2. preserve local metadata/manifests
3. preserve cached material
4. expose degraded state
5. retain provider references
6. permit verified-copy evacuation
7. support catalog/index rebuild from manifests
8. avoid treating Telegram message history as the only index

---

# 6. rclone strategy

**Integrate, do not rebuild.**

Use rclone for mature transfer/protocol primitives such as:

- copy/move where explicitly authorized
- filtering
- retries
- bandwidth limits
- checksums
- remote backends
- WebDAV/S3/etc. adapters
- crypt where appropriate
- mount/VFS when explicitly configured
- transfer logging and operational controls

TelDrive Lab owns:

- policy
- authorization
- durable jobs
- provenance
- verification evidence
- catalog/index
- audit
- organization
- recovery
- provider evacuation planning
- product-level health

Never turn rclone into an arbitrary shell execution surface.

---

# 7. WebDAV and HTTP decision

HTTP/API is core because the Lab already has a control-plane API surface.

WebDAV is **important interoperability work**, but implementation must follow an architecture review. It should be a thin authenticated/rate-limited adapter over the Lab/provider abstraction, not a new storage engine.

Minimum useful WebDAV semantics if implemented:

- authenticated access
- list
- read
- range/chunked read where supported
- write/upload through controlled jobs
- move/copy only through explicit policy
- delete only through explicit authorization
- bounded concurrency
- clear consistency behavior
- auditability

Do not implement SMB/NFS merely to claim protocol breadth.

---

# 8. Search strategy

Preferred stack for a personal installation:

```text
metadata
  ↓
SQLite structured queries
  ↓
SQLite FTS5 / lexical search
  ↓
OCR + transcript + subtitle text
  ↓
optional local embeddings
  ↓
optional AI query interpretation
```

Avoid mandatory Elasticsearch/OpenSearch-class infrastructure. It adds resource and maintenance cost without matching the target workload.

Search must remain useful with **zero AI providers**.

---

# 9. Automation boundary

TelDrive Lab should own workflows about **its own storage semantics**:

- backup
- archive
- verify
- index
- snapshot
- safe organization
- recovery planning
- provider health response

It should expose events/hooks for cross-system workflows instead of becoming a generic automation platform.

Example:

```text
TelDrive Lab
   │
   ├── job.completed
   ├── integrity.failed
   ├── provider.degraded
   ├── backup.verified
   └── archive.ready
             │
             ▼
     external automation
```

---

# 10. Exhaustive product completeness matrix

Status meanings:

- 🟢 **IMPLEMENTED + TESTED** — concrete implementation and regression/host coverage
- 🟢 **IMPLEMENTED** — concrete implementation, provider-dependent or with lighter coverage
- 🟡 **ADAPTER / CONTRACT** — boundary exists but external system is not a full integration
- 🟡 **PARTIAL** — meaningful implementation exists but product capability is incomplete
- 🟠 **EXPERIMENTAL** — intentionally non-core research/prototype
- 🔴 **DOCUMENTED BUT NOT IMPLEMENTED** — vision/docs exist, implementation does not
- ⚪ **FUTURE / IDEA** — not currently committed

| Feature | Category | Current implementation | Evidence | User value | Dependency | Risk | Effort | ₹0 feasibility | Recommended action | Priority |
|---|---|---|---|---|---|---|---|---|---|---|
| Durable jobs | Core | Real durable queue/leases/retries | Phase 3 gates | Very high | SQLite/local runtime | Low | M | Yes | Maintain | MUST |
| Transfer boundary | Core | Controlled local/rclone execution | Phase 4 gate | Very high | rclone optional | Medium | M | Yes | Harden | MUST |
| Organization planner | Core | Deterministic policy + dry-run | Phase 5 | High | Local metadata | Medium | M | Yes | Maintain | MUST |
| Archive workflow | Core | One-way durable archive | Phase 6 | High | Transfer manager | Medium | M | Yes | Productize | MUST |
| Integrity evidence | Core | SHA-256 evidence + verification | Phase 7 | Very high | Local I/O | Low | M | Yes | Expand coverage | MUST |
| Duplicate reports | Core | SHA-256 + size grouping | Phase 7 | High | Catalog/checksums | Medium | S | Yes | Keep report-only | MUST |
| Destructive deduplication | Lifecycle | Not enabled | Safety invariant | Medium | Authorization | High | L | Yes | Do not automate | DO NOT |
| Lifecycle safety | Core | Retention/quarantine/purge boundaries | Phase 8 | Very high | Job/policy layers | High | M | Yes | Maintain | MUST |
| Backups | Core | Durable scheduled backup + verification | Phase 9 | Very high | Jobs/checksums | Medium | M | Yes | Productize | MUST |
| Snapshots/restore planning | Recovery | Manifests + restore dry-run | Phase 9/19 | Very high | Local state | High | M | Yes | Drill regularly | MUST |
| Monitoring/health | Core | Health metrics + alerts | Phase 10 | High | Host/runtime | Low | M | Yes | Productize | MUST |
| CLI/control plane | Core | Safe operator CLI | Phase 11 | Very high | Core services | Low | M | Yes | Stabilize | MUST |
| Hot/cold intelligence | Storage intelligence | Implemented | Phase 12 | Medium | Access data | Low | M | Yes | Maintain | SHOULD |
| Read-only API | Interop | Implemented | Phase 13/22 | High | Local service | Medium | M | Yes | Stabilize contract | MUST |
| Local IPC | Interop | Contract/implementation | Phase 13 | Medium | OS runtime | Low | S | Yes | Maintain | SHOULD |
| Metadata export/import | Resilience | Implemented | Phase 13 | High | Catalog | Low | S | Yes | Productize | MUST |
| Media discovery | Media | Implemented | Phase 14 | High | Local scanning | Low | M | Yes | Harden | SHOULD |
| Media metadata | Media | Implemented/provider-aware | Phase 14 | High | ffprobe optional | Low | S | Yes | Maintain | SHOULD |
| Subtitle indexing | Media | Implemented | Phase 14/16 | Medium | File parsing | Low | S | Yes | Maintain | SHOULD |
| Thumbnail generation | Media | Capability/provider | Phase 14 | Medium | Local tools | Medium | M | Yes | Optional | COULD |
| Jellyfin integration | Media | Contract/adapter groundwork | Phase 14 | Very high | Jellyfin | Medium | M | Yes | Build thin integration | SHOULD |
| Plex integration | Media | Contract/optional groundwork | Phase 14 | Medium | Plex | Medium | M | Yes | Deprioritize | COULD |
| Full OTT | Media | Not implemented | Product strategy | High but huge | Many | Very high | XL | Poor | Do not build | DO NOT |
| Custom media player | Media | Not implemented | Product strategy | Medium | Web/media stack | High | XL | Poor | Delegate | DO NOT |
| Transcoding pipeline | Media | Not implemented | Product strategy | High | FFmpeg/GPU | Very high | XL | Poor | Delegate to Jellyfin/FFmpeg | DO NOT |
| Watch history/profiles | Media | Not implemented | Product strategy | Medium | App DB/auth | Medium | L | Yes | Delegate | DO NOT |
| HTTP media range access | Interop | Partial/read-oriented | API foundation | Very high | Provider semantics | High | M | Yes | Implement carefully | MUST |
| WebDAV | Interop | Not a full server | Docs/strategy | Very high | Provider abstraction | High | L | Yes | Thin adapter after review | MUST |
| S3 adapter/gateway | Interop | Not full | Strategy | Medium | S3 semantics | Medium | L | Yes | Later | COULD |
| FUSE | Interop | Experimental/optional direction | Strategy | Medium | Kernel/FUSE | High | L | Yes | Experiment only | EXPERIMENT |
| SMB/NFS | Interop | Not implemented | Strategy | Low/medium | Protocol servers | High | XL | Poor | Do not build | DO NOT |
| rclone transfer integration | Interop | Implemented controlled boundary | Phase 4 | Very high | rclone | Medium | M | Yes | Expand supported safe operations | MUST |
| rclone replacement | Core | Not intended | Strategy | Low | Huge | Very high | XL | Poor | Do not build | DO NOT |
| OCR | Intelligence | Local adapter | Phase 15 | Medium | Tesseract | Low | M | Yes | Optional | SHOULD |
| Speech-to-text | Intelligence | Local adapter | Phase 15 | Medium | Whisper/local runtime | Medium | M/L | Conditional | Optional | COULD |
| Local embeddings | Intelligence | Deterministic local implementation | Phase 15/16 | Medium | CPU/RAM | Medium | M | Yes | Keep optional | COULD |
| Visual fingerprints | Intelligence | Implemented | Phase 15 | Low/medium | Local compute | Medium | M | Yes | Deprioritize expansion | COULD |
| Lexical/content search | Search | Implemented | Phase 16 | Very high | SQLite/local tools | Low | M | Yes | Productize | MUST |
| Semantic search | Search | Implemented local-vector path | Phase 16 | High | Local embeddings | Medium | M | Yes | Improve only after lexical | SHOULD |
| AI natural-language search | AI | Advisory implementation | Phase 17 | High | Optional local model | Medium | M | Yes | Keep optional | SHOULD |
| AI organization suggestions | AI | Advisory proposals | Phase 17 | Medium/high | Optional local model | High | M | Yes | Keep advisory | SHOULD |
| Autonomous AI mutation | AI | Forbidden | Safety invariant | Negative | None | Extreme | XL | No need | Do not build | DO NOT |
| Storage forecasting | Analytics | Implemented | Phase 18 | Medium | Historical metadata | Low | S | Yes | Maintain | COULD |
| Storage heatmaps | Analytics | Implemented | Phase 18 | Medium | Catalog | Low | S | Yes | Maintain | COULD |
| Reclaim estimates | Analytics | Implemented report | Phase 18 | Medium | Duplicate index | Medium | S | Yes | Keep advisory | COULD |
| Provider abstraction | Resilience | Partly implicit; needs product-level contract | Architecture | Very high | Core adapters | Medium | L | Yes | Make explicit | MUST |
| Provider-independent manifest | Resilience | Partial via catalog/snapshots | Architecture | Very high | Catalog | Low | M | Yes | Promote to canonical contract | MUST |
| Provider evacuation | Resilience | Planning direction | Strategy | Very high | Provider abstraction | High | L | Yes | Build early | MUST |
| Flood/backpressure handling | Resilience | Job/retry foundations | Strategy | Very high | Telegram behavior | High | M/L | Yes | Make provider-aware | MUST |
| Telegram health/capability status | Resilience | Partial | Monitoring/provider work | Very high | Telegram adapter | Medium | M | Yes | Build | MUST |
| Unlimited Telegram promise | Product | Not valid | Strategy | Negative | None | Extreme | — | No | Never claim | DO NOT |
| Local cache/materialization | Performance | Planning/capability foundations | Phase 12 | Very high | Disk/cache | Medium | M | Yes | Productize | MUST |
| Media prefetch | Performance | Suggestion/capability foundation | Phase 12/14 | Medium/high | Access data | Medium | M | Yes | Add after cache | SHOULD |
| Event/webhook system | Automation | Contract/direction | Phases 10/21/22 | High | API | Medium | M | Yes | Build | MUST |
| Scheduled ingestion | Automation | Durable-job foundations | Phase 3/6/9 | High | Jobs/watchers | Medium | M | Yes | Productize | SHOULD |
| Archive watcher | Automation | Planned workflow | Phase 6 docs | Medium | Local FS | Medium | M | Yes | Build | SHOULD |
| Generic workflow engine | Automation | Not intended | Strategy | Low | Huge | High | XL | Poor | Do not build | DO NOT |
| Notifications | Operations | Local/free mechanisms | Phase 10 | Medium | Desktop/webhook | Low | S | Yes | Maintain | SHOULD |
| CAS storage replacement | Experimental | Prototype/foundation | Phase 21 | Medium | Storage redesign | Very high | XL | Conditional | Keep experimental | EXPERIMENT |
| Advanced tiering | Experimental | Advisory/experimental | Phase 21 | Medium | Provider abstraction | High | L | Yes | Defer | EXPERIMENT |
| Distributed workers | Experimental | Registry/dispatch groundwork | Phase 21 | Medium | Network/trust | Very high | XL | Conditional | Defer | EXPERIMENT |
| Remote worker mutation | Experimental | Not trusted by default | Safety invariant | Medium | Strong auth | Extreme | XL | Conditional | Defer | EXPERIMENT |
| AI workflow orchestration | Experimental | Contract/plan | Phase 21 | Medium | Local AI | Very high | XL | Yes | Narrow only | EXPERIMENT |
| Control-center UI | Productization | Minimal local implementation | Phase 22 | Very high | Local HTTP/API | Medium | M/L | Yes | Productize | MUST |
| Mobile app | Clients | Not implemented | Strategy | Medium | API/auth | High | XL | Conditional | PWA/API first | COULD |
| Public multi-user service | Product | Not intended | Strategy | Low | Auth/billing/ops | Extreme | XL | No | Do not build | DO NOT |
| Paid AI dependency | Constraint | Forbidden | Project constraint | Negative | Paid API | High | — | No | Never introduce | DO NOT |

---

# 11. Priority stack

## MUST — build next

1. Productized installation/configuration/capability detection
2. Provider abstraction and explicit capability model
3. Provider-independent manifests and export
4. Telegram-aware rate/backpressure/degraded-state handling
5. Local cache/materialization modes
6. Provider evacuation/migration workflow
7. Stable HTTP/API contract
8. Safe WebDAV adapter after architecture validation
9. Control-center UX over existing control plane
10. Event/webhook surface
11. Jellyfin integration tooling
12. Media-aware cache/prefetch
13. Search consolidation and operational polish
14. Backup/restore drills
15. Honest capacity/reliability messaging

## SHOULD

- OCR/transcription integrations
- natural-language search
- advisory AI explanations
- archive watcher
- notifications
- media metadata/thumbnail enrichment
- verified-copy dashboards

## COULD

- S3 adapter
- lightweight browser preview
- mobile/PWA client
- advanced analytics

## EXPERIMENT

- CAS optimization
- tiering
- distributed workers
- FUSE
- advanced AI orchestration

## DO NOT BUILD

- full OTT
- custom transcoding platform
- custom media-server/player ecosystem
- rclone replacement
- custom POSIX filesystem
- SMB/NFS server
- general automation platform
- autonomous destructive AI
- Telegram abuse/evasion mechanisms
- public multi-tenant Telegram storage service
- mandatory paid APIs/services
- large search clusters for a personal installation

---

# 12. What “complete” means

TelDrive Lab should be called **product-complete** only when the following are true:

### Reliability

- install/upgrade is repeatable
- jobs survive restarts
- retries/backpressure are provider-aware
- degraded providers do not corrupt Lab state

### Trust

- every mutation has policy and authorization
- every successful transfer has verification evidence where applicable
- audit history is durable
- recovery has been tested, not merely documented

### Interoperability

- stable API
- mature rclone consumption
- safe WebDAV interoperability
- provider-independent manifests
- verified migration/evacuation path

### Storage

- local cache/materialization is predictable
- Telegram is replaceable
- duplicate/integrity intelligence is authoritative at the Lab layer
- catalog is rebuildable

### Media

- media discovery and metadata are solid
- Jellyfin integration is straightforward
- Lab does not duplicate Jellyfin's playback responsibilities

### Intelligence

- deterministic search works without AI
- AI is optional and advisory
- explanations and suggestions are bounded and auditable

### Operations

- control center is usable
- health/degraded states are obvious
- notifications are free/local by default
- documentation describes real capabilities rather than aspirational ones

**Product completeness does not require building every item in the matrix.** Some items are deliberately excluded because building them would make the product worse, less safe, or less maintainable.

---

# 13. Zero-cost feasibility policy

₹0 means more than “no subscription.” Every feature must be evaluated against:

- CPU cost
- RAM cost
- disk growth
- network bandwidth
- maintenance burden
- dependency availability
- model size/runtime cost
- operational complexity
- hidden cloud/API requirements

A feature is not considered zero-cost if its practical operation depends on a paid service, paid inference, paid hosting, or an unavoidable recurring external charge.

Local open-source tooling is preferred when it fits the hardware. Heavy local models remain optional and must never become core dependencies.

---

# 14. Architectural traps to avoid

1. **Feature-count optimization** — do not add protocols merely to increase the matrix.
2. **OTT gravity** — media features must not turn into a second Jellyfin.
3. **Telegram lock-in** — never make Telegram message history the only authoritative index.
4. **rclone duplication** — do not recreate mature transfer functionality.
5. **AI authority creep** — natural-language convenience must not become mutation authority.
6. **Distributed-worker premature optimization** — stabilize local semantics first.
7. **CAS premature replacement** — reporting and evidence are useful; replacing storage is a separate project.
8. **Protocol explosion** — WebDAV/HTTP are useful; SMB/NFS are not justified by the target product.
9. **Microservice explosion** — a personal local control plane should remain operationally simple.
10. **False completeness** — contracts/adapters are not the same as production integrations.
11. **Hidden paid dependency** — no silent cloud fallback.
12. **Destructive convenience** — safer friction is preferable to irreversible automation.

---

# 15. Final product statement

> **TelDrive Lab is a local-first, auditable storage control plane that turns heterogeneous storage—including Telegram-backed storage—into manageable personal archives, backup workflows, and media integrations.**

Its moat is not another file browser or media player. Its moat is **trustworthy storage operations**:

```text
Durable execution
+ provider independence
+ authoritative local metadata
+ verification evidence
+ safe policy/authorization
+ recovery
+ auditability
+ intelligent search
+ mature interoperability
```

That is the product to build.

Everything else must justify its existence against that core.